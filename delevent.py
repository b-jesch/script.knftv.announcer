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
    message = handler.RequestConnector()
    message.announcement = args
    result = message.sendRequest()

    if result:
        fetched = result['items']
        if len(fetched) > 0:

            menu = list()

            for item in fetched:
                liz = xbmcgui.ListItem(label=item['Title'], label2='%s - %s' % (item['ChannelName'], item['Date']))
                liz.setArt({'icon': item['Icon']})
                liz.setProperty('file', item['File'])
                menu.append(liz)

            _idx = xbmcgui.Dialog().select(handler.loc(30042), menu, useDetails=True)
            if _idx > -1:
                broadcast.update({'file': menu[_idx].getProperty('file')})
                args.update({'command': 'del', 'broadcast': handler.sanitize(broadcast)})
                message.announcement = args
                result = message.sendRequest()
            else:
                result = False
                message.status = None
        else:
            result = False
            message.status = handler.loc(30025)

    if not result:
        handler.notifyLog('Broadcast could\'nt deleted')
        handler.notifyOSD(handler.loc(30000), message.status, icon=handler.IconAlert)
    else:
        handler.notifyLog('Broadcast deleted')
        handler.notifyOSD(handler.loc(30000), message.status, icon=handler.IconOk)
