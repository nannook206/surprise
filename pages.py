"""
These are functions to return HTML pages.
"""

def header(meta=''):
    return """
        <html>
        %s
        <head>
          <style>
            p {font-family: sans-serif; font-size: 2rem;}
            .btn {
              width: 40%%
              height: 10%%
              border: 2px solid black;
              background-color: #eee;
              padding: 14px 28px;
              font-size: 3.5rem;
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
        <p style="font-size:3rem">Surprise</p>
        <p id="timer"></p>
        <p id="status"></p>
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
        <script>
            var ws = new WebSocket("ws://192.168.0.26:8889/");
            ws.onmessage = function (event) {
                var fields = event.data.match(/([^:]*):(.*)/);
                var element = document.getElementById(fields[1])
                if (element != null) element.innerHTML = fields[2];
            };
        </script>
        <script type="text/javascript">
            function playSound () {
                document.getElementById('beep').play();
            }
        </script>
        </body>
        </html>
        """

def idle(surprise):
    if surprise.locked:
        return header() + buttons(['Activate']) + trailer()
    else:
        return (header() + buttons(['Activate', 'Lock']) +
                '<br>' + buttons(['On', 'Off']) +
                '<br>' + buttons(['Down', 'Up']) + trailer())

def waiting(surprise):
    if surprise.locked:
        return header() + buttons(['Start']) + trailer()
    else:
        return header() + buttons(['Start', 'Reset']) + trailer()

def status(surprise):
    if surprise.locked:
        return header() + buttons(['Down', 'Up']) + trailer()
    else:
        return header() + buttons(['Reset', 'Down', 'Up']) + trailer()
                
