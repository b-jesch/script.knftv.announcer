#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import handler

if __name__ ==  '__main__':

    handler.notifyLog('Context menu called: del event')

    # fetch own announcements

    args = dict()
    broadcast = dict()
    args.update({'command': 'fetch'})
    bc = handler.cRequestConnector()
    result = bc.transmitAnnouncement(args)

    if result is not None:
        fetched = result['items']
        if len(fetched) > 0:

            menu = list()

            for item in fetched:
                liz = xbmcgui.ListItem(label=item['Title'], label2='%s - %s' % (item['ChannelName'], item['Date']))
                liz.setArt({'icon': item['Icon']})
                liz.setProperty('file', item['File'])
                menu.append(liz)

            _idx = xbmcgui.Dialog().select(30042, menu, useDetails=True)
            if _idx > -1:
                broadcast.update({'file': menu[_idx].getProperty('file')})
                args.update({'command': 'del', 'broadcast': handler.sanitize(broadcast)})
                result = bc.transmitAnnouncement(args)
            else:
                exit(0)
        else:
            result = None

    if result is None:
        handler.notifyLog('Broadcast could\'nt deleted')
        handler.notifyOSD(30000, bc.status, icon=handler.IconAlert)
    else:
        handler.notifyLog('Broadcast deleted')
        handler.notifyOSD(30000, bc.status, icon=handler.IconOk)
