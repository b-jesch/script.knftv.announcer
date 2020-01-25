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

OSD = xbmcgui.Dialog()
LI = xbmcgui.ListItem()

def date2timeStamp(date, dFormat=None, utc=False):
    # Kodi bug: returns '%H%H' or '%I%I'

    if dFormat is None:
        # use Kodi's own dateformat provided by setup
        df = xbmc.getRegion('dateshort') + ' ' + xbmc.getRegion('time').replace('%H%H', '%H').replace('%I%I','%I').replace(':%S', '')
    else:
        df = dFormat
    dtt = time.strptime(date, df)
    if not utc: return int(time.mktime(dtt))
    return int(time.mktime(dtt)) + UTC_OFFSET

def notifyLog(message, level=xbmc.LOGDEBUG):
    xbmc.log('[%s %s] %s' % (addonid, version, message), level)

def notifyOSD(header, message, icon=IconDefault, time=5000):
    OSD.notification(header, message, icon, time)

def sanitize(dict):
    for key, val in dict.items():
        try:
            dict.update({key: val.replace('&', '&amp;')})
        except AttributeError:
            continue
    return dict


class RequestAnnouncer(object):

    def __init__(self):
        self.server = addon.getSetting('server')
        self.nickname = addon.getSetting('nickname')
        self.id = unicode(addon.getSetting('id'))
        self.status = 'ok'

        if not self.id.isnumeric() or int(self.id) == 0:
            self.id = str(int(time.time()))[-8:]
            addon.setSetting('id', self.id)

        self.announcement = dict()

    def sendBroadcast(self):

        # check broadcast

        if self.announcement['command'] == 'add':

            utime = date2timeStamp(self.announcement['broadcast']['date'])
            self.announcement.update({'utime': utime})

            if (not utime or (utime - int(time.time()) < TIMEDELAY)):
                self.status = loc(30022)
                return False

        self.announcement.update({'id': self.id, 'nickname': self.nickname})
        js = json.dumps(self.announcement, sort_keys=True, indent=4)
        headers = {'content-type': 'application/json'}
        try:
            req = requests.post(self.server, json=js, headers=headers, timeout=5)
            req.raise_for_status()

            if req.status_code == 403:
                self.status = loc(30023)
                return False

            elif req.status_code == 200:
                js = json.loads(req.text)
                response = js.get('result', 'failure')
                print response

                if response == 'ok':
                    self.status = loc(30020)
                    return js

                self.status = loc(30021)
                return False

        except requests.ConnectTimeout as e:
            notifyLog(e, xbmc.LOGERROR)
            self.status = loc(30024)

        except requests.HTTPError as e:
            notifyLog(e, xbmc.LOGERROR)
            self.status = loc(30021)

        except ValueError as e:
            notifyLog(e, xbmc.LOGERROR)
            self.status = loc(30024)

        return False
