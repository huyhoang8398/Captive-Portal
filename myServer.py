import sys, os, socket
import urllib.request
import urllib.parse
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi
from bs4 import BeautifulSoup


def getToken():
    request = urllib.request.Request('https://cas.unilim.fr')
    rep = urllib.request.urlopen(request)
    html_response = BeautifulSoup(rep.read(), "html.parser")
    token_val = html_response.find(id="token").get('value')
    print("Token: " + token_val)
    return token_val


def getCookies(username, password, token):
    cookieProcessor = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(cookieProcessor)
    data = urllib.parse.urlencode({'user': username, 'password': password, 'token': token})
    request = urllib.request.Request('https://cas.unilim.fr', bytes(data, encoding='ascii'))
    reponse = opener.open(request)
    cookies = [c for c in cookieProcessor.cookiejar if c.name == 'lemonldap']
    return cookies


PORT_NUMBER = 8080  # the PORT_NUMBER in which the captive portal web server listens
# IFACE      = "wlan2"      # the interface that captive portal protects
SERVER_ADDRESS = "10.10.10.1"  # the ip address of the captive portal (it can be the IP of IFACE)
token = ""  # token value get from 1st connection


class CaptivePortal(BaseHTTPRequestHandler):
    # the login page
    html_login = b"""
	<html>
  <head>
    <title>Login to Captive Portal</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link
      href="https://fonts.googleapis.com/css?family=Press+Start+2P"
      rel="stylesheet"
    />
    <link
      href="https://unpkg.com/nes.css@2.3.0/css/nes.min.css"
      rel="stylesheet"
    />
    <style>
      html,
      body {
        font-family: "Press Start 2P", cursive;
        background-color: #f7f1e3;
        height: 100%;
        width: 100%;
        margin: 0;
      }
      body,
      body {
        display: flex;
      }
      form {
        margin: auto;
      }
    </style>
  </head>
  <body>
      <form method="POST" action="do_login">
        <h2 class="nes-text is-primary">Login to use the internet</h2>
        <div class="nes-field">
          <label for="username">Username</label>
          <input type="text" id="username" class="nes-input" name="username" />
        </div>
        <div class="nes-field">
          <label for="username">Password</label>
          <input
            type="password"
            id="password"
            class="nes-input"
            name="password"
          />
        </div>
        <input style="margin-top: 10px;"
          type="submit"
          value="Submit"
          type="button"
          class="nes-btn is-primary"
        />
      </form>
  </body>
</html>
	"""
    html_success_login_page = b"""
    <html>
  <head>
    <title>Login success</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link
      href="https://fonts.googleapis.com/css?family=Press+Start+2P"
      rel="stylesheet"
    />
    <link
      href="https://unpkg.com/nes.css@2.3.0/css/nes.min.css"
      rel="stylesheet"
    />
    <style>
      html,
      body {
        font-family: "Press Start 2P", cursive;
        background-color: #f7f1e3;
        height: 100%;
        width: 100%;
        margin: 0;
      }
      body,
      body {
        display: flex;
      }
      h2 {
        margin: auto;
      }
    </style>
  </head>
  <body>
    <h2 class="nes-text is-success">Login success, Now you can use the internet!</h2>
  </body>
</html>
    """

    html_login_failed = b"""
    	<html>
  <head>
    <title>Login to Captive Portal</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link
      href="https://fonts.googleapis.com/css?family=Press+Start+2P"
      rel="stylesheet"
    />
    <link
      href="https://unpkg.com/nes.css@2.3.0/css/nes.min.css"
      rel="stylesheet"
    />
    <style>
      html,
      body {
        font-family: "Press Start 2P", cursive;
        background-color: #f7f1e3;
        height: 100%;
        width: 100%;
        margin: 0;
      }
      body,
      body {
        display: flex;
      }
      form {
        margin: auto;
      }
    </style>
  </head>
  <body>
      <form method="POST" action="do_login">
        <h2 class="nes-text is-error">Login failed please re-enter your email or your password</h2>
        <div class="nes-field">
          <label for="username">Username</label>
          <input type="text" id="username" class="nes-input" name="username" />
        </div>
        <div class="nes-field">
          <label for="username">Password</label>
          <input
            type="password"
            id="password"
            class="nes-input"
            name="password"
          />
        </div>
        <input style="margin-top: 10px;"
          type="submit"
          value="Submit"
          type="button"
          class="nes-btn is-primary"
        />
      </form>
  </body>
</html>
    """

    def do_GET(self):
        # 1st connection
        global token
        token = getToken()
        # 2nd connection
        path = self.path
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(self.html_login)

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     })
        username = form.getvalue("username")
        password = form.getvalue("password")
        global token
        if (not getCookies(username, password, token)):  # login failed.
            self.wfile.write(self.html_login_failed)
        else:  # login success
            remote_IP = self.client_address[0]
            print('New authorization from ' + remote_IP)
            print('Updating IP tables')
            subprocess.call(["iptables", "-t", "nat", "-I", "PREROUTING", "1", "-s", remote_IP, "-j", "ACCEPT"])
            subprocess.call(["iptables", "-I", "FORWARD", "-s", remote_IP, "-j", "ACCEPT"])
            print('IP tables updated')
            self.wfile.write(self.html_success_login_page)


print("*********************************************")
print("* Note, if there are already iptables rules *")
print("* this script may not work. Flush iptables  *")
print("* at your own risk using iptables -F        *")
print("*********************************************")
print("Updating iptables")
print(".. Block all traffic")
subprocess.call(["iptables", "-I", "FORWARD", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"])
print(".. Setup private net work")
subprocess.call(["iptables", "-t", "nat", "-A", "POSTROUTING", "-s", "10.10.10.0/24", "-j", "MASQUERADE"])
print(".. Allow TCP DNS")
subprocess.call(["iptables", "-A", "FORWARD", "-s", "10.10.10.0/24", "-p", "tcp", "--dport", "53", "-j", "ACCEPT"])
print(".. Allow UDP DNS")
subprocess.call(["iptables", "-A", "FORWARD", "-s", "10.10.10.0/24", "-p", "udp", "--dport", "53", "-j", "ACCEPT"])
print("Starting web server")
httpd = HTTPServer(('', PORT_NUMBER), CaptivePortal)
print("Redirecting HTTP traffic to captive portal")
subprocess.call(
    ["iptables", "-t", "nat", "-A", "PREROUTING", "-s", "10.10.10.0/24", "-p", "tcp", "--dport", "80", "-j", "DNAT",
     "--to-destination", SERVER_ADDRESS + ":" + str(PORT_NUMBER)])
subprocess.call(
    ["iptables", "-t", "nat", "-A", "PREROUTING", "-s", "10.10.10.0/24", "-p", "tcp", "--dport", "443", "-j", "DNAT",
     "--to-destination", SERVER_ADDRESS + ":" + str(PORT_NUMBER)])

try:
    print("Serving at port ", PORT_NUMBER)
    httpd.serve_forever()
except KeyboardInterrupt:
    pass
httpd.server_close()
