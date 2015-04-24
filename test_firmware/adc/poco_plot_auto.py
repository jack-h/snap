#!/usr/bin/env python
'''
This script demonstrates grabbing data off an already configured FPGA and plotting it using Python. Designed for use with CASPER workshop Tutorial 4.
\n\n 
Author: Jason Manley, August 2009.
Modified: Aug 2012, Nie Jun
'''

#TODO: add support for coarse delay change
#TODO: add support for ADC histogram plotting.
#TODO: add support for determining ADC input level 

import corr,time,numpy,struct,sys,logging,pylab,matplotlib

katcp_port=7147

def exit_fail():
    print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
    try:
        fpga.stop()
    except: pass
    raise
    exit()

def exit_clean():
    try:
        fpga.stop()
    except: pass
    exit()

def get_data():
    acc_n = fpga.read_uint('acc_num')
    print 'Grabbing integration number %i'%acc_n

    d = numpy.zeros([12, 1024], dtype=numpy.complex)
    for i in range(6):
        d_r = numpy.array(struct.unpack('>2048l', fpga.read('dir_x0_x%d%d_real'%(i,i), 2048*4)))
        d_i = numpy.array(struct.unpack('>2048l', fpga.read('dir_x0_x%d%d_imag'%(i,i), 2048*4)))
        d[2*i] = d_r[0:1024] + 1j*d_i[0:1024]
        d[2*i+1] = d_r[1024:2048] + 1j*d_i[1024:2048]

    return acc_n, d

def drawDataCallback():
    print 'hello!'
    matplotlib.pyplot.clf()
    acc_n, data  = get_data()

    for i in range(12):
        matplotlib.pyplot.subplot(4,3,1+i)
        if ifch:
            matplotlib.pyplot.plot(10*numpy.log10(data[i]))
            matplotlib.pyplot.xlim(0,1024)
            matplotlib.pyplot.xlabel('Channel')
        else:
            matplotlib.pyplot.plot(xaxis,10*numpy.log10(data[i]))
            matplotlib.pyplot.xlabel('Frequency')
        matplotlib.pyplot.grid()
        matplotlib.pyplot.title('Integration number %i \nAnt %d'%(acc_n, i))
        matplotlib.pyplot.ylabel('Power (arbitrary units)')

    matplotlib.pyplot.draw()

    #fig.canvas.manager.window.after(100, drawDataCallback)

if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser()
    p.set_usage('poco_plot_auto.py <ROACH_HOSTNAME_or_IP> [options]')
    p.set_description(__doc__)
    p.add_option('-C','--channel',dest='ch',action='store_true',
        help='Set plot with channel number or frequency.')
    p.add_option('-f','--frequency',dest='fr',type='float',default=400.0,
        help='Set plot max frequency.(If -c sets to False)')
    opts, args = p.parse_args(sys.argv[1:])

    if args==[]:
        print 'Please specify a ROACH board. \nExiting.'
        exit()
    else:
        roach = args[0]

    if opts.ch !=None:
        ifch = opts.ch
    else:
        ifch = False

    if ifch == False:
        if opts.fr != '':
            maxfr = opts.fr
        else:
            maxfr = 400.0
        xaxis = numpy.arange(0.0, maxfr, maxfr*1./1024)

# What to be shown on X axis while ploting
# ifch means if the X axis is channel number

try:
    loggers = []
    lh=corr.log_handlers.DebugLogHandler()
    logger = logging.getLogger(roach)
    logger.addHandler(lh)
    logger.setLevel(10)

    print('Connecting to server %s on port %i... '%(roach,katcp_port)),
    fpga = corr.katcp_wrapper.FpgaClient(roach, katcp_port, timeout=10,logger=logger)
    time.sleep(1)

    if fpga.is_connected():
        print 'ok\n'
    else:
        print 'ERROR connecting to server %s on port %i.\n'%(roach,katcp_port)
        exit_fail()


    prev_integration = fpga.read_uint('acc_num')
    print 'Last integration:', prev_integration


    # set up the figure with a subplot for each polarisation to be plotted
    print 'Setting up figure'
    fig = matplotlib.pyplot.figure()

    drawDataCallback()

    # start the process
    print 'Starting draw process'
    #fig.canvas.manager.window.after(100, drawDataCallback)
    print 'Calling show()'
    matplotlib.pyplot.show()
    print 'Exiting...'

except AttributeError:
    pass
except KeyboardInterrupt:
    exit_clean()
except:
    exit_fail()

exit_clean()

