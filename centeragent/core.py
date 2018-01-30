#
# core.py
#
# Copyright (C) 2009 Date Huang <tjjh89017@hotmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

import urllib
import urllib2
import json
from twisted.internet.task import LoopingCall

from deluge.log import LOG as log
from deluge.plugins.pluginbase import CorePluginBase
import deluge.component as component
import deluge.configmanager
from deluge.core.rpcserver import export

DEFAULT_PREFS = {
    "IP": "",
    "Port": 3124
}

class Core(CorePluginBase):
    def enable(self):
        self.config = deluge.configmanager.ConfigManager("centeragent.conf", DEFAULT_PREFS)
        self.session = component.get("Core").session
        self.alertmanager = component.get("AlertManager")

        # connect to Center via HTTP
        self.connect(self.config["IP"], self.config["Port"])

        # polling timer every 5 min
        self.polling_timer = LoopingCall(self.polling)
        self.polling_timer.start(300)

    def disable(self):
        self.polling_timer.stop()
        pass

    def update(self):
        pass

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        for key in config.keys():
            self.config[key] = config[key]
        self.config.save()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config

    def connect(self, ip, port):
        log.info("Connecting...")
        self.url = "http://" + ip + ":" + str(port)

        response = urllib2.urlopen(self.url + "/register/")
        r = json.loads(response.read())

        if r['result'] == 'OK':
            log.info("Connect to Center SUCCESS")
            return True
        return False

    def fn(self, handle):
        if not handle.is_valid():
            return None
        status = handle.status()
        if status.is_finished:
            return None
        if not status.has_metadata:
            return None
        return handle

    def report(self):

        log.info("Report")
        jobs = len(filter(self.fn, self.session.get_torrents()))
        response = urllib2.urlopen(self.url + "/report/?" + urllib.urlencode({'jobs': jobs}))

        pass

    def on_save_resume_data_alert_factory(self, _save_path):

        save_path = _save_path

        def on_save_resume_data_alert(alert):
            # send to Center with save_path
            # TODO
            pass

        return on_save_resume_data_alert

    def add_torrent(self, torrent_resume_data, save_path):

        pass

    def migrate(self):
        log.info("Send job")
        
        # check if need to send a job to another
        while True:
            response = urllib2.urlopen(self.url + "/check/")
            r = json.loads(response)
            if r['result'] == "NO":
                break

            jobs = filter(self.fn, self.session.get_torrents())
            if len(jobs) <= 0:
                break

            torrent = jobs[0]
            torrent.pause()
            torrent.flush_cache()
            torrent.save_resume_data(3)
            save_path = torrent.status().save_path
            self.alertmanager.register_handler("save_resume_data_alert", self.on_save_resume_data_alert_factory(save_path))

        log.info("Recv job")
        # check if need to recv job

        response = urllib2.urlopen(self.url + "/recv/")
        r = json.loads(response)

        if r['result'] == "NO":
            return
        for a, b in r['jobs']:
            self.add_torrent(a, b)

        pass

    def polling(self):
        log.info("Polling")
        if self.url:
            self.report()
            self.migrate()
