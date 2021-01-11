# I. Introduction 

## Context and Motivation

A captive portal is a web page accessed with a web browser that is displayed to newly connected users of a Wi-Fi or wired network before they are granted broader access to network resources. Captive portals are commonly used to present a landing or log-in page which may require authentication, payment, acceptance of an end-user license agreement, acceptable use policy, survey completion, or other valid credentials that both the host and user agree to to redirect users of a network that provides outbound internet access to a web page that displays the terms of service.

# II. Configuring network

![Network Architecture](graph.png)

# III. Configuring DHCP Server and DNS Service


```bash
sudo dnsmasq -d -z -i meth0 -F 10.10.10.10,10.10.10.20
```

![Execute dnsmasq for DHCP](./report_imgs/DHCP_VM.png)

```bash
sudo ip netns exec hA dhclient -d hA-eth0 
sudo ip netns exec hB dhclient -d hB-eth0
```

For tracing the packet exchanges, we use tcpdump on the DHCP server for port 67 or 68, the result is shown below

![A trace of the packet exchanges on the DHCP server](./report_imgs/DHCP_tcpdump.png){ width=70% }

# III. Configuring Firewall

For configuring the firewall, we set some rules in NAT and FILTER table.

```bash
sudo iptables -I FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
sudo iptables -t nat -A POSTROUTING -s 10.10.10.0/24 -j MASQUERADE (private network)
sudo iptables -A FORWARD -s 10.10.10.0/24 -p tcp --dport 53 -j ACCEPT
sudo iptables -A FORWARD -s 10.10.10.0/24 -p udp --dport 53 -j ACCEPT
```

For redirecting traffic from the private network to the destination of the Web:

```bash
sudo iptables -t nat -A PREROUTING -s 10.10.10.0/24 -p tcp --dport 80 -j DNAT --to-destination 10.10.10.1:8080
sudo iptables -t nat -A PREROUTING -s 10.10.10.0/24 -p tcp --dport 443 -j DNAT --to-destination 10.10.10.1:8080
```

![Nat tables before config](./report_imgs/nattables_beforeConfig.png)

![Nat tables after config](./report_imgs/nattables_afterConfig.png)

![Nat tables after authentication](./report_imgs/nattables_afterAuth.png)

The result below shows an output of the "iptables -nL" command for the different modified tables as before config, after config and after authentication.

![IP Tables before config](./report_imgs/iptables_beforeConfig.png)

![IP Tables after config](./report_imgs/iptables_afterConfig.png)

![IP Tables after authentication](./report_imgs/iptables_afterAuth.png)

# IV. TCP Server

In this section, we implement a TCP server which serve a login page for client request to access a website in external network.
In order to authenticate, we use a perform secure authentication with CAS Unilim server by using `LemonLDAP`

```python
def getCookies(username, password, token):
    cookieProcessor = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(cookieProcessor)
    data = urllib.parse.urlencode({'user': username, 'password': password, 'token': token})
    request = urllib.request.Request('https://cas.unilim.fr', bytes(data, encoding='ascii'))
    reponse = opener.open(request)
    cookies = [c for c in cookieProcessor.cookiejar if c.name == 'lemonldap']
    return cookies
```

If the client logins successfully, we will update our firewall with the `remote_IP` and redirect to a successful webpage otherwise, the client will be returned to a login page with a alert message.

![Login page](./report_imgs/login.png)

![Success page](./report_imgs/success.png)

![Failed page](./report_imgs/failed.png)

