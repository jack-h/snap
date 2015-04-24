import corr
import time
import pylab
import struct
import numpy as np

r = corr.katcp_wrapper.FpgaClient('apjhpi.ra.phy.private.cam.ac.uk')

time.sleep(0.2)

for chip in range(3):
    for chan in range(4):
        pylab.subplot(3,4, 1 + 4*chip + chan)
        d = np.array(struct.unpack('>1024b', r.read('adc16_wb_ram%d'%chip, 1024))[chan::4])
        for j in range(2):
            print 'Channel %d:%d:%d'%(chip, chan,j),
            for i in range(16):
                print np.binary_repr(d[j+2*i], width=8),
            print ''

            pylab.plot(d[j::2])
        pylab.title('Chip %d, channel %d'%(chip, chan))
    print ''

pylab.show()
