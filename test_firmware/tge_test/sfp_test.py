#!/bin/env ipython

'''
This script demonstrates programming an FPGA, configuring 10GbE cores and checking transmitted and received data using the Python KATCP library along with the katcp_wrapper distributed in the corr package. Designed for use with TUT3 at the 2009 CASPER workshop.
\n\n 
Author: Jason Manley, August 2009.
Updated for CASPER 2013 workshop. This tut needs a rework to use new snap blocks and auto bit unpack.
'''
import corr, time, struct, sys, logging, socket

#Decide where we're going to send the data, and from which addresses:
#base_ip  = 10*(2**24) + 0*(2**16) + 0*(2**8)
base_ip  = 192*(2**24) + 168*(2**16) + 5*(2**8)
#mac_base = (2<<40) + (2<<32)
mac_base=0x123456780000

pkt_period = 16384  #how often to send another packet in FPGA clocks (100MHz)
payload_len = 128   #how big to make each packet in 64bit words

fabric_port=10000

boffile = 'sfp4x_test.bof'
fpga=[]

def exit_fail():
    print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
    exit()

def exit_clean():
    try:
        for f in fpgas: f.stop()
    except: pass
    exit()

if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser()
    p.set_usage('tut2.py <ROACH_HOSTNAME_or_IP> [options]')
    p.set_description(__doc__)
    p.add_option('-p', '--noprogram', dest='noprogram', action='store_true',
        help='Don\'t reprogram the fpga.')
    p.add_option('-c', '--noct', dest='noct', action='store_true',
        help='Disable corner turn -- just send packets between pairs of ports.')
    p.add_option('-n', '--ncores', dest='ncores', type='int', default=8,
        help='Number of ethernet cores')  
    p.add_option('-T', '--period', dest='period', type='int', default=16384,
        help='How often to send packets (in 155MHz FPGA clocks)')  
    p.add_option('-P', '--payload', dest='payload', type='int', default=128,
        help='Payload of each packet (in 64 bit words)')  
    p.add_option('-a', '--arp', dest='arp', action='store_true',
        help='Print the ARP table and other interesting bits.')  
    p.add_option('-b', '--boffile', dest='bof', type='str', default=boffile,
        help='Specify the bof file to load')  
    opts, args = p.parse_args(sys.argv[1:])

    if args==[]:
        print 'Please specify a ROACH board. \nExiting.'
        exit()
    else:
        roach = args[0]
    if opts.bof != '':
        boffile = opts.bof
try:
    lh = corr.log_handlers.DebugLogHandler()
    logger = logging.getLogger(roach)
    logger.addHandler(lh)
    logger.setLevel(10)

    print('Connecting to server %s... '%(roach)),
    fpga = corr.katcp_wrapper.FpgaClient(roach, logger=logger, timeout=20)
    time.sleep(1)

    if fpga.is_connected():
        print 'ok\n'
    else:
        print 'ERROR connecting to server %s.\n'%(roach)
        exit_fail()
    
    if not opts.noprogram:
        print '------------------------'
        print 'Programming FPGA...',
        sys.stdout.flush()
        fpga.progdev(boffile)
        time.sleep(0.1)
        print 'ok'

    print '---------------------------'    
    print 'Disabling output...',
    sys.stdout.flush()
    for i in range(opts.ncores):
       fpga.write_int('pkt_sim%d_enable'%i, 0)
    print 'done'

    print '---------------------------'    

    sys.stdout.flush()
    for i in range(opts.ncores):
        print 'Configuring core gbe%d'%i
        #fpga.tap_start('tap0','gbe%d'%i,mac_base+i,base_ip+i,fabric_port)
        fpga.write('gbe%d'%i, struct.pack('>Q', mac_base+i), offset=0)
        fpga.write('gbe%d'%i, struct.pack('>L', base_ip+i), offset=0x10)
        for j in range(opts.ncores):
            mac_str = struct.pack('>Q', mac_base+j)
            fpga.write('gbe%d'%i, mac_str, offset=(0x3000+8*j))

    print '---------------------------'

    print 'Setting-up packet source...',
    sys.stdout.flush()
    fpga.write_int('period',opts.period)
    fpga.write_int('payload_len',opts.payload)
    print 'done'
    print 'Enable corner turn?', not opts.noct
    fpga.write_int('ct_en', int(not opts.noct))

    print 'Setting-up destination addresses...',
    sys.stdout.flush()
    #fpga.write_int('dest_ip_base',(base_ip>>8)<<5)
    fpga.write_int('dest_ip_base',base_ip)
    fpga.write_int('dest_port',fabric_port)
    print 'done'

    print 'Resetting cores and counters...',
    sys.stdout.flush()
    fpga.write_int('rst', 3)
    print 'done'

    print 'Enabling output...',
    for i in range(opts.ncores):
        sys.stdout.flush()
        fpga.write_int('pkt_sim%d_enable'%i, 1)
    print 'done'

    fpga.write_int('rst', 4) # resets off, tx enable on
    fpga.write_int('rst', 5) # reset counters again (to get rid of the first rogue crc fail)
    fpga.write_int('rst', 4) # resets off, tx enable on
    reset_time = time.time()

    fpga_rate = 100.#fpga.est_brd_clk()
    print 'fpga clock rate: %.2f'%fpga_rate
    packet_rate = fpga_rate*1e6/opts.period
    bit_rate = packet_rate * 64 * (opts.payload+1) #plus one because crc is added to the end
    total_bit_rate = packet_rate * (64*(opts.payload+1) + 54*8)
    print 'Packet rate: %d packets/sec'%packet_rate
    print 'Bit rate: %d bits/sec (%.2fGb/s)'%(bit_rate, bit_rate/1e9)
    print 'Bit rate (with overhead): %d bits/sec (%.2fGb/s)'%(total_bit_rate, total_bit_rate/1e9)

    while(True):
        for i in range(opts.ncores):
            sent = fpga.read_int('tx_frame_cnt%d'%i)
            received = fpga.read_int('rx_frame_cnt%d'%i)
            errors = fpga.read_int('rx_frame_err%d'%i)
            txof = fpga.read_int('tx_of%d'%i)
            rxof = fpga.read_int('tx_of%d'%i)
            bad_crc_cnt = fpga.read_int('crc_check%d_bad_cnt'%i)
            tx_minus_rx = fpga.read_int('tx_minus_rx%d'%i)
            print 'After %d seconds: Core %d, sent %d, received %d, errors %d, bad crcs %d, tx-rx %d, (txof=%d, rxof=%d)'%(time.time() - reset_time,i,sent,received,errors,bad_crc_cnt,tx_minus_rx,txof,rxof)
        print '###############################'
        time.sleep(1)

except KeyboardInterrupt:
    #for i in range(opts.ncores):
    #    fpga.print_10gbe_core_details('gbe%d'%i, arp=True)
    exit_clean()
except Exception as inst:
    print type(inst)
    print inst.args
    print inst
    exit_fail()

exit_clean()

