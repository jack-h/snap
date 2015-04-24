import corr
import time
import pylab
import struct
import numpy as np

r = corr.katcp_wrapper.FpgaClient('apjhpi.ra.phy.private.cam.ac.uk')

time.sleep(0.2)

for chip in range(3):
    for chan in range(4):
        #pylab.subplot(3,4, 1 + 4*chip + chan)
        d = np.array(struct.unpack('>1024b', r.read('adc16_wb_ram%d'%chip, 1024))[chan::4])
        print 'Channel %d:%d'%(chip, chan),
        for i in range(16):
            print np.binary_repr(d[i], width=8),
        print ''

        pylab.plot(d, label='ADC%d'%(4*chip + chan))
        #pylab.title('Chip %d, channel %d'%(chip, chan))
    print ''

pylab.ylim(-128,128)
pylab.legend()
pylab.show()
