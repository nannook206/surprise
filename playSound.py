import logging
import subprocess


def playSound(file):
    try:
        completed = subprocess.run(['/usr/bin/mpg123', '-q', 'sounds/%s.mp3' % file])
    except OSError as e:
        logging.error('playSound failed: %s' % e)

