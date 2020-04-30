import logging
import subprocess

'''
Used http://www.fromtexttospeech.com/ with voice 'Daisy' to generate my mp3 files
'''
def playSound(file):
    try:
        completed = subprocess.run(['/usr/bin/mpg123', '-q', 'sounds/%s.mp3' % file])
    except OSError as e:
        logging.error('playSound failed: %s' % e)

