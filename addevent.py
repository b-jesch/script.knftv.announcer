#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys

import xbmc
import handler
import re

if __name__ == '__main__':

    handler.notifyLog('Context menu called: add event')
    handler.notifyLog('Local time format of client: {}'.format(handler.regionDateFormat()))

    channel = xbmc.getInfoLabel('ListItem.Channelname')
    args = dict()
    broadcast = dict()

    # removing additional infos of channelnames faced in Parentheses, eg. (ger) or (deu)

    broadcast.update({'channelname': re.sub(r'\([^()]*\)', '', channel).strip(),
                      'icon': xbmc.getInfoLabel('ListItem.Icon'),
                      'date': handler.date2JTF(xbmc.getInfoLabel('ListItem.Date')),
                      'starttime': handler.date2JTF(xbmc.getInfoLabel('ListItem.StartTime'), timeonly=True),
                      'endtime': handler.date2JTF(xbmc.getInfoLabel('ListItem.EndTime'), timeonly=True),
                      'title': xbmc.getInfoLabel('ListItem.Title'),
                      'epgeventtitle': xbmc.getInfoLabel('ListItem.EpgEventTitle'),
                      'genre': xbmc.getInfoLabel('ListItem.Genre'),
                      'plot': xbmc.getInfoLabel('ListItem.Plot'),
                      'rating': xbmc.getInfoLabel('ListItem.Rating'),
                      })

    # check for additional events (pvr connection required)

    pvr = handler.cPvrConnector()
    pvr.channelName2channeldId(channel)
    if pvr.channel_id is not None:
        pvr.getBroadcasts(broadcast['epgeventtitle'], handler.date2timeStamp(broadcast['date']))
        if len(pvr.broadcasts) > 0: broadcast.update({'broadcasts': pvr.broadcasts})

    # check online availability of images and move to server cache

    bc = handler.cRequestConnector()

    # check if nickname is set
    if not bc.nickname:
        handler.notifyOSD(30000, 30144, icon=handler.IconAlert)
        sys.exit()

    response = bc.transmitFile([broadcast['icon'], pvr.channel_logo, handler.FALLBACK])
    if response is not None:
        broadcast.update({'icon': response['items'], 'icontype': response['icontype']})

    # determine ratings

    if broadcast['rating'] != '':
        broadcast.update({'rating': float(broadcast['rating']) if int(broadcast['rating']) < 10 else float(int(broadcast['rating']) / 10.0)})

    args.update({'command': 'add', 'broadcast': handler.sanitize(broadcast)})
    if args['broadcast'].get('icon', None) is None or bc.transmitAnnouncement(args) is None:
        handler.notifyLog('Broadcast could\'nt delivered')
        handler.notifyOSD(30000, bc.status, icon=handler.IconAlert)
    else:
        handler.notifyLog('Broadcast delivered')
        handler.notifyOSD(30000, bc.status, icon=handler.IconOk)
