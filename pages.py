"""
These are functions to return HTML pages.
"""

def header(meta=''):
    return """
        <html>
        %s
        <head>
          <style>
            p {font-family: sans-serif; font-size: 4rem;}
            .btn {
              width: 40%%
              height: 10%%
              border: 2px solid black;
              background-color: #eee;
              padding: 14px 28px;
              font-size: 4rem;
              border-radius: 8px;
              cursor: pointer;
              display: inline-block;
              margin: 10px
            }

            .activate {color: green;}
            .start {color: green;}
            .reset {color: red;}
            .default {color: black;}
          </style>
          <title> Surprise </title>
        </head>
        <body>
        <audio id="beep" src="beep.wav" preload="auto"></audio>
        <center>
        """ % meta

def buttons(names):
    string = "\n"
    for name in names:
        string += '<button class="btn %s" onclick="playSound()" name=action value="%s">%s</button>' % (
                 name.lower(), name.lower(), name) + "\n"
    return '<form method="get" action="/"> %s </form>' % string

def trailer():
    return """
        </center>
        <script type="text/javascript">
            function playSound () {
                document.getElementById('beep').play();
            }
        </script
        </body>
        </html>
        """

def idle(surprise):
    if surprise.locked:
        return header() + '<p>Surprise</p>' + buttons(['Activate']) + trailer()
    else:
        return (header() + '<p>Surprise</p>' + buttons(['Activate', 'Lock']) +
                '<br>' + buttons(['On', 'Off']) + trailer())

def waiting(surprise):
    if surprise.locked:
        return header() + '<p>Surprise</p>' + buttons(['Start']) + trailer()
    else:
        return header() + '<p>Surprise</p>' + buttons(['Start', 'Reset']) + trailer()

def status(surprise):
    if surprise.locked:
        return (header('<meta http-equiv="refresh" content="5; URL=/">') +
                '<p>Surprise</p><p>%s</p>' % surprise.state + trailer())
    else:
        return (header('<meta http-equiv="refresh" content="1; URL=/">') +
                """
                <p>Surprise</p>
                <p><small>%s for %d seconds.<br>%d remaining<br>%d secs total</small></p>
                """ % surprise.timerStatus() +
                buttons(['Reset']) + trailer())
