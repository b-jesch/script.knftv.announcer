#!/usr/bin/python

import time
import datetime
import xbmc
import xbmcaddon
import xbmcgui
from random import randint
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

        utime = date2timeStamp(self.announcement['date'])

        if not utime or (utime - int(time.time()) < TIMEDELAY):
            notifyOSD(loc(30000), loc(30022))
            return False

        self.announcement.update({'id': self.id, 'nickname': self.nickname, 'utime': utime})
        js = json.dumps(self.announcement, sort_keys=True, indent=4)
        headers = {'content-type': 'application/json'}
        try:
            req = requests.post(self.server, json=js, headers=headers)
            req.raise_for_status()

            print(req.text)
            self.status = req.status_code
            if self.status == 403:
                notifyOSD(loc(30000), loc(30023))
                return False

            elif self.status == 200:
                js = json.loads(req.text)
                response = js.get('result', 'failure')

                if response == 'ok':
                    notifyOSD(loc(30000), loc(30020))
                    return True

                notifyOSD(loc(30000), loc(30021))
                return False

        except requests.HTTPError as e:
            notifyLog(e, xbmc.LOGERROR)
            notifyOSD(loc(30000), loc(30021))

        except ValueError as e:
            notifyLog(e, xbmc.LOGERROR)
            notifyOSD(loc(30000), loc(30024))

        return False