#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import handler

if __name__ ==  '__main__':

    handler.notifyLog('Context menu called: add event')
    args = dict()
    broadcast = dict()
    broadcast.update({'channelname': xbmc.getInfoLabel('ListItem.ChannelName'), 'icon': xbmc.getInfoLabel('ListItem.Icon'),
                      'date': xbmc.getInfoLabel('ListItem.Date'), 'starttime': xbmc.getInfoLabel('ListItem.StartTime'),
                      'endtime': xbmc.getInfoLabel('ListItem.EndTime'), 'title': xbmc.getInfoLabel('ListItem.Title'),
                      'epgeventtitle': xbmc.getInfoLabel('ListItem.EpgEventTitle'), 'genre': xbmc.getInfoLabel('ListItem.Genre'),
                      'plot': xbmc.getInfoLabel('ListItem.Plot'),
                      })

    args.update({'command': 'add', 'broadcast': handler.sanitize(broadcast)})
    message = handler.RequestAnnouncer()
    message.announcement = args
    if not message.sendBroadcast():
        handler.notifyLog('Broadcast could\'nt delivered')
        handler.notifyOSD(handler.loc(30000), message.status, icon=handler.IconAlert)
    else:
        handler.notifyLog('Broadcast delivered')
        handler.notifyOSD(handler.loc(30000), message.status, icon=handler.IconOk)
