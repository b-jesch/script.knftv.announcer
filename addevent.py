#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import handler

if __name__ ==  '__main__':

    handler.notifyLog('Context menu called: add event')
    args = dict()
    args.update({'channelname': xbmc.getInfoLabel('ListItem.ChannelName'), 'icon': xbmc.getInfoLabel('ListItem.Icon'),
                 'date': xbmc.getInfoLabel('ListItem.Date'), 'starttime': xbmc.getInfoLabel('ListItem.StartTime'),
                 'endtime': xbmc.getInfoLabel('ListItem.EndTime'), 'title': xbmc.getInfoLabel('ListItem.Title'),
                 'epgeventtitle': xbmc.getInfoLabel('ListItem.EpgEventTitle'), 'genre': xbmc.getInfoLabel('ListItem.Genre'),
                 'plot': xbmc.getInfoLabel('ListItem.Plot'),
                 })

    message = handler.RequestAnnouncer()
    message.announcement = args
    if not message.sendBroadcast():
        handler.notifyLog('Broadcast could\'nt delivered')
    else:
        handler.notifyLog('Broadcast delivered')
