#!/usr/bin/python

import time
import xbmc
import xbmcaddon
import xbmcgui
import json
import requests
import os

from urllib import unquote_plus
from urlparse import urlsplit

addon = xbmcaddon.Addon()
addonid = addon.getAddonInfo('id')
version = addon.getAddonInfo('version')
path = xbmc.translatePath(addon.getAddonInfo('path'))
loc = addon.getLocalizedString

IconDefault = os.path.join(path, 'resources', 'media', 'default.png')
IconAlert = os.path.join(path, 'resources', 'media', 'alert.png')
IconOk = os.path.join(path, 'resources', 'media', 'ok.png')
FALLBACK = os.path.join(path, 'fanart.jpg')

TIMEDELAY = 3600    # min timediff for future broadcasts
JSON_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
JSON_DATETIME_FORMAT_SHORT = '%Y-%m-%d %H:%M'
JSON_TIME_FORMAT_SHORT = '%H:%M'
UTC_OFFSET = -time.timezone

UPLOAD_PATH = 'upload.php'

OSD = xbmcgui.Dialog()
LI = xbmcgui.ListItem()


def regionTimeFormat():
    # Kodi bug: returns '%H%H' or '%I%I' sometimes
    return xbmc.getRegion('time').replace('%H%H', '%H').replace('%I%I', '%I').replace(':%S', '')


def regionDateFormat():

    return '{} {}'.format(xbmc.getRegion('dateshort'), regionTimeFormat())


def date2timeStamp(date, dFormat=JSON_DATETIME_FORMAT_SHORT, utc=False):

    try:
        dtt = time.strptime(date, dFormat)
    except ValueError:
        try:
            dtt = time.strptime(date, regionDateFormat())
        except ValueError:
            dtt = 0
    finally:
        if not utc: return int(time.mktime(dtt))
        return int(time.mktime(dtt)) + UTC_OFFSET


def date2JTF(date, timeonly=False):
    if timeonly:
        dtt = time.strptime(date, regionTimeFormat())
        return time.strftime(JSON_TIME_FORMAT_SHORT, dtt)
    else:
        dtt = time.strptime(date, regionDateFormat())
        return time.strftime(JSON_DATETIME_FORMAT_SHORT, dtt)


def jsonrpc(query):
    querystring = {"jsonrpc": "2.0", "id": 1}
    querystring.update(query)
    return json.loads(xbmc.executeJSONRPC(json.dumps(querystring, encoding='utf-8')))


def notifyLog(message, level=xbmc.LOGDEBUG):
    try:
        xbmc.log('[%s %s] %s' % (addonid, version, message.encode('utf-8')), level)
    except AttributeError:
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
                    if channel['label'] == channelname:
                        self.channel_id = channel['channelid']
                        query = {
                            "method": "PVR.GetChannelDetails",
                            "params": {"channelid": self.channel_id, "properties": ["thumbnail"]},
                        }
                        res = jsonrpc(query)
                        if 'result' in res:
                            details = res['result'].get('channeldetails', None)
                            if details is not None:
                                _netloc = urlsplit(unquote_plus(details.get('thumbnail', FALLBACK))).netloc
                                _path = urlsplit(unquote_plus(details.get('thumbnail', FALLBACK))).path
                                self.channel_logo = '{}{}'.format(_netloc, _path)

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
                    if broadcast['title'] == title.decode('utf-8'):
                        starttime = round(date2timeStamp(broadcast['starttime'], dFormat=JSON_DATETIME_FORMAT, utc=True) // 60.0) * 60
                        if starttime != utime:
                            self.broadcasts.append(time.strftime(JSON_DATETIME_FORMAT_SHORT, time.gmtime(starttime + UTC_OFFSET)))


class cRequestConnector(object):

    def __init__(self):
        self.server = addon.getSetting('server')
        self.nickname = addon.getSetting('nickname')
        self.id = unicode(addon.getSetting('id'))
        self.status = 30150

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
        notifyLog('Transmit announcement to {}'.format(self.server))
        return self.sendRequest(url=self.server, js=js, headers=headers)

    def transmitFile(self, filelist):
        for file in filelist:
            notifyLog('Transmit {} to {}'.format(file, self.server))
            try:
                req_f = requests.get(file, stream=True)
                req_f.raise_for_status()
                response = self.sendRequest(url=self.server + UPLOAD_PATH, files={'icon': req_f.raw})
                if response is None:
                    notifyLog('Status code: '.format(self.status), xbmc.LOGERROR)
                    continue
                elif 30101 <= response['code'] <= 30103:
                    notifyLog(response['code'])
                    continue
                else:
                    response.update({'icontype': filelist.index(file)})
                    return response
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
                notifyLog(str(e), xbmc.LOGERROR)
            except requests.exceptions.MissingSchema:
                response = self.sendRequest(url=self.server + UPLOAD_PATH, files={'icon': open(file, 'rb').read()})
                if response is None:
                    notifyLog('Status code: '.format(self.status), xbmc.LOGERROR)
                    continue
                elif 30101 <= response['code'] <= 30103:
                    notifyLog(response['code'])
                    continue
                else:
                    response.update({'icontype': filelist.index(file)})
                    return response
        return None

    def sendRequest(self, url=None, js=None, headers=None, files=None):

        try:
            req = requests.post(url, json=js, headers=headers, files=files, timeout=5)
            req.raise_for_status()

            response = json.loads(req.text)
            self.status = response.get('code', 30150)
            notifyLog('Result: %s: Code: %s' % (response.get('result', 'undef'), response.get('code', 30150)))
            return response

        except requests.exceptions.ConnectTimeout as e:
            notifyLog(str(e), xbmc.LOGERROR)
            self.status = 30140

        except requests.exceptions.HTTPError as e:
            if req.status_code == 403: self.status = 30142
            elif req.status_code == 404: self.status = 30141
            else: self.status = 30143
            notifyLog(str(e), xbmc.LOGERROR)

        except ValueError as e:
            notifyLog(str(e), xbmc.LOGERROR)
            self.status = 30143

        except AttributeError as e:
            notifyLog(str(e), xbmc.LOGERROR)
            self.status = 30143

        return None
