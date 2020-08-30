#!/usr/bin/python

import time
import datetime
import xbmc
import xbmcaddon
import xbmcgui
import json
import requests
import os

addon = xbmcaddon.Addon()
addonid = xbmcaddon.Addon().getAddonInfo('id')
version = xbmcaddon.Addon().getAddonInfo('version')
path = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path'))
loc = xbmcaddon.Addon().getLocalizedString

IconDefault = os.path.join(path, 'resources', 'media', 'default.png')
IconAlert = os.path.join(path, 'resources', 'media', 'alert.png')
IconOk = os.path.join(path, 'resources', 'media', 'ok.png')

TIMEDELAY = 3600    # min timediff for future broadcasts
JSON_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
UTC_OFFSET = int(round((datetime.datetime.now() - datetime.datetime.utcnow()).seconds, -1))

MAIN_PATH = 'index.php'
UPLOAD_PATH = 'upload.php'

OSD = xbmcgui.Dialog()
LI = xbmcgui.ListItem()


def regionDateFormat():

    # Kodi bug: returns '%H%H' or '%I%I' sometimes

    return xbmc.getRegion('dateshort') + ' ' + xbmc.getRegion('time').replace('%H%H', '%H').replace('%I%I', '%I').replace(':%S', '')


def date2timeStamp(date, dFormat=regionDateFormat(), utc=False):

    dtt = time.strptime(date, dFormat)
    if not utc: return int(time.mktime(dtt))
    return int(time.mktime(dtt)) + UTC_OFFSET


def jsonrpc(query):
    querystring = {"jsonrpc": "2.0", "id": 1}
    querystring.update(query)
    return json.loads(xbmc.executeJSONRPC(json.dumps(querystring)))


def notifyLog(message, level=xbmc.LOGDEBUG):
    xbmc.log('[%s %s] %s' % (addonid, version, message), level)


def notifyOSD(header, message, icon=IconDefault, time=5000):
    OSD.notification(loc(header), loc(message), icon, time)


def sanitize(dict, exclude=None):

    if exclude is None: exclude = list()
    for key, val in dict.items():
        if len(exclude) > 0 and key in exclude: continue
        try:
            dict.update({key: val.replace('&', '&amp;')})
        except AttributeError:
            continue
    return dict


class cPvrConnector(object):

    def __init__(self):
        self.channel_id = None
        self.broadcasts = list()

    def channelName2channeldId(self, channelname):

        query = {
                'method': 'PVR.GetChannels',
                'params': {'channelgroupid': 'alltv'},
                }

        res = jsonrpc(query)
        if 'result' in res:
            channels = res['result'].get('channels', False)
            if channels:
                for channel in channels:
                    if channel['label'] == channelname: self.channel_id = channel['channelid']

    def getBroadcasts(self, title, utime):

        query = {
                'method': 'PVR.GetBroadcasts',
                'params': {'channelid': self.channel_id, 'properties': ['title', 'starttime']}
                }

        res = jsonrpc(query)
        if 'result' in res:
            broadcasts = res['result'].get('broadcasts', False)
            if broadcasts:
                for broadcast in broadcasts:
                    if broadcast['title'] == title:
                        starttime = round(date2timeStamp(broadcast['starttime'], dFormat=JSON_TIME_FORMAT, utc=True) / 60.0) * 60
                        if starttime != utime:
                            self.broadcasts.append(datetime.datetime.fromtimestamp(starttime).strftime(regionDateFormat()))


class cRequestConnector(object):

    def __init__(self):
        self.server = addon.getSetting('server')
        self.nickname = addon.getSetting('nickname')
        self.id = addon.getSetting('id')
        self.status = 'ok'

        if not self.id.isnumeric() or int(self.id) == 0:
            self.id = str(int(time.time()))[-8:]
            addon.setSetting('id', self.id)

        if self.server[-1] != '/':
            self.server = '{}/'.format(self.server)
            addon.setSetting('server', self.server)

        self.Pvr = cPvrConnector()

    def transmitAnnouncement(self, announcement):

        # check broadcast

        if announcement['command'] == 'add':

            utime = date2timeStamp(announcement['broadcast']['date'])
            announcement.update({'utime': utime})

            if not utime or (utime - int(time.time()) < TIMEDELAY):
                self.status = 30117
                return None

        announcement.update({'id': self.id, 'nickname': self.nickname})
        js = json.dumps(announcement, sort_keys=True, indent=4)
        headers = {'content-type': 'application/json'}
        notifyLog('Transmit announcement to server...')
        return self.sendRequest(url=self.server, js=js, headers=headers)

    def transmitFile(self, fromURL):

        if fromURL is None: return None
        try:
            notifyLog('Transmit resource file to server...')
            req_f = requests.get(fromURL, stream=True)
            req_f.raise_for_status()

            result = self.sendRequest(url=self.server + UPLOAD_PATH, files={'icon': req_f.raw})
            if result is not None:
                return result.get('items', None)

        except requests.exceptions.ConnectionError as e:
            notifyLog(str(e), xbmc.LOGERROR)
            self.status = 30140

        except requests.exceptions.HTTPError as e:
            notifyLog(str(e), xbmc.LOGERROR)
            self.status = 30141

        return None

    def sendRequest(self, url=None, js=None, headers=None, files=None):

        try:
            req = requests.post(url, json=js, headers=headers, files=files, timeout=5)
            notifyLog(req.text)
            req.raise_for_status()

            js = json.loads(req.text)
            response = js.get('result', 'failure')
            self.status = js.get('code', 30150)
            if response == 'ok': return js

        except requests.exceptions.ConnectTimeout as e:
            notifyLog(str(e), xbmc.LOGERROR)
            self.status = 30140

        except requests.exceptions.HTTPError as e:
            self.status = 30141
            if req.status_code == 403: self.status = 30142
            elif req.status_code == 404: self.status = 30140
            notifyLog(str(e), xbmc.LOGERROR)

        except ValueError as e:
            notifyLog(str(e), xbmc.LOGERROR)
            self.status = 30143

        except AttributeError as e:
            notifyLog(str(e), xbmc.LOGERROR)
            self.status = 30143

        return None


