#!/usr/bin/python
# Copyright 2015 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Collectd plugin for getting resource statistics from Glance
if __name__ == '__main__':
    import collectd_fake as collectd
else:
    import collectd

import collectd_openstack as openstack

PLUGIN_NAME = 'openstack_glance'
INTERVAL = openstack.INTERVAL


class GlanceStatsPlugin(openstack.CollectdPlugin):
    """ Class to report the statistics on Glance service.

        number of image broken down by state
        total size of images usable and in error state
    """

    def __init__(self, *args, **kwargs):
        super(GlanceStatsPlugin, self).__init__(*args, **kwargs)
        self.plugin = PLUGIN_NAME
        self.interval = INTERVAL
        self.pagination_limit = 25

    def itermetrics(self):

        def default_metrics(suffix=''):
            ret = {}
            for name in ('snapshots', 'images'):
                for visibility in ('public', 'private',
                                   'community', 'shared'):
                    for status in ('active', 'queued', 'saving',
                                   'killed', 'deleted', 'deactivated',
                                   'pending_delete'):
                        key = '%s%s.%s.%s' % (name, suffix,
                                              visibility, status)
                        ret[key] = 0
            return ret

        def is_snap(d):
            return d.get('image_type') == 'snapshot'

        def groupby(d):
            p = d['visibility']
            status = d.get('status', 'unknown').lower()
            if is_snap(d):
                return 'snapshots.%s.%s' % (p, status)
            return 'images.%s.%s' % (p, status)

        images_details = self.get_objects('glance', 'images',
                                          api_version='v2',
                                          params={},
                                          detail=False)
        status = self.count_objects_group_by(images_details,
                                             group_by_func=groupby)
        if len(status) == 0:
            status = default_metrics()
        for s, nb in status.iteritems():
            (name, visibility, state) = s.split('.')
            yield {
                'plugin_instance': name,
                'values': nb,
                'meta': {'visibility': visibility, 'state': state,
                         'discard_hostname': True}
            }

        # sizes
        def count_size_bytes(d):
            return d.get('size', 0)

        def groupby_size(d):
            p = d['visibility']
            status = d.get('status', 'unknown').lower()
            if is_snap(d):
                return 'snapshots_size.%s.%s' % (p, status)
            return 'images_size.%s.%s' % (p, status)

        sizes = self.count_objects_group_by(images_details,
                                            group_by_func=groupby_size,
                                            count_func=count_size_bytes)
        if len(sizes) == 0:
            sizes = default_metrics('_size')
        for s, nb in sizes.iteritems():
            (name, visibility, state) = s.split('.')
            yield {
                'plugin_instance': name,
                'values': nb,
                'meta': {'visibility': visibility, 'state': state,
                         'discard_hostname': True},
            }

plugin = GlanceStatsPlugin(collectd, PLUGIN_NAME, disable_check_metric=True)


def config_callback(conf):
    plugin.config_callback(conf)


def notification_callback(notification):
    plugin.notification_callback(notification)


def read_callback():
    plugin.conditional_read_callback()

if __name__ == '__main__':
    import time
    collectd.load_configuration(plugin)
    plugin.read_callback()
    collectd.info('Sleeping for {}s'.format(INTERVAL))
    time.sleep(INTERVAL)
    plugin.read_callback()
    plugin.shutdown_callback()
else:
    collectd.register_config(config_callback)
    collectd.register_notification(notification_callback)
    collectd.register_read(read_callback, INTERVAL)
