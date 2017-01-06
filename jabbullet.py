import sleekxmpp
from sleekxmpp import ClientXMPP
import pushbullet
import os
import time
import logging
import sys

log = logging.getLogger(__name__)

class Config: pass
class Device: pass

def env(name):
    return os.environ[name]

def push_note(config, title, note):
    log.info('pushing to {} + {} with {} {}'.format(config.pushbullet_api,
        config.pushbullet_device, title, note))
    # quick hack to give an object that pushbullet.py expects
    device = Device()
    device.device_iden = config.pushbullet_device

    pb = pushbullet.Pushbullet(config.pushbullet_api)
    pb.push_note(title, note, device=device)

def get_config():
    config = Config()
    config.pushbullet_api = env('PUSHBULLET_API')
    config.pushbullet_device = env('PUSHBULLET_DEVICE')
    config.username = env('XMPP_USERNAME')
    config.password = env('XMPP_PASSWORD')
    config.nickname = env('XMPP_MUC_NICKNAME')
    config.chats = env('XMPP_MUC_ROOMS').split(',')
    config.muc_domain = env('XMPP_MUC_DOMAIN')
    config.targets = env('TARGETS').split(',')
    return config

def join_rooms_on_connect_handler(bot, muc, muc_domain, rooms_to_join, nick):
    def join_rooms_on_connect(event):
        log.info('getting roster')
        bot.get_roster()
        log.info('sending presence')
        bot.send_presence(ppriority=0)
        log.info('joining rooms ..')
        for room in rooms_to_join:
            full_room = room + '@' + muc_domain 
            log.info(' .. joining ' + full_room)
            muc.joinMUC(full_room, nick, wait=True)
    return join_rooms_on_connect

def on_message_handler(config):
    def on_message(message_stanza):
        if message_stanza['type'] == 'error':
            log.error(message_stanza)

        if not message_stanza['body']:
            log.error('apparently empty message: '+str(message_stanza))

        if message_stanza['subject']:
            log.debug('ignoring room subject')
            return

        body = message_stanza['body']
        user = message_stanza['mucnick'] or message_stanza['from']

        log.debug('got message {} from {}'.format(body, user))

        if any(target in body.lower() for target in config.targets):
            log.info('found a match!')
            push_note(config, str(user) + ' sent you a message', body)
    return on_message
        

def xmpp_connect(config):
    bot = ClientXMPP(config.username, config.password)
    bot.register_plugin('xep_0045')
    muc = bot.plugin['xep_0045']
    bot.register_plugin('xep_0199')
    ping = bot.plugin['xep_0199']
    ping.enable_keepalive(30, 30)

    bot.add_event_handler('session_start',
            join_rooms_on_connect_handler(bot, muc, config.muc_domain,
                config.chats, config.nickname))
    bot.add_event_handler('message', on_message_handler(config))

    if not bot.connect():
        raise 'could not connect'

    return bot


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    config = get_config()
    bot = xmpp_connect(config)

    bot.process(block=True)

