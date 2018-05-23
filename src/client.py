#!/usr/bin/env python3

import os
from time import sleep
from select import select
import argparse
import libtorrent as lt


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('torrents', nargs="*")

    parser.add_argument('-p', '--port', type=int, default=6881,
                        help='set listening port')

    parser.add_argument('-d', '--max-download-rate', type=float, default=0,
                        help='the maximum download rate given in kB/s.'
                        '0 means infinite.')

    parser.add_argument('-u', '--max-upload-rate', type=float, default=0,
                        help='the maximum upload rate given in kB/s.'
                        '0 means infinite.')

    parser.add_argument('-s', '--save-path', type=str, default=".",
                        help='the path to save the downloaded file/folder')

    parser.add_argument('-a', '--allocation-mode', type=str,
                        help='sets mode for allocating the downloaded files'
                        'Possible args are [full | compact]',
                        default='compact')

    parser.add_argument('-r', '--proxy-host', type=str,
                        help="sets HTTP proxy host and port"
                        "(separated by :)", default='')

    args = parser.parse_args()
    return args


def load_arguments():
    args = parse_arguments()
    args.max_upload_rate *= 1000
    args.max_download_rate *= 1000

    if args.port < 0 or args.port > 65525:
        args.port = 6881

    if args.max_upload_rate <= 0:
        args.max_upload_rate = -1

    if args.max_download_rate <= 0:
        args.max_download_rate = -1

    return args


def proxy_setup(proxy_host):
    proxy_settings = lt.proxy_settings()
    proxy_settings.type = lt.proxy_type.http
    hostname, port = proxy_host.split(':')
    proxy_settings.hostname, proxy_settings.port = hostname, int(port)
    return proxy_settings


def torrent_handles():
    args = load_arguments()
    settings = lt.session_settings()
    settings.user_agent = 'python_client/' + lt.version

    session = lt.session()
    session.set_settings(settings)
    session.set_download_rate_limit(int(args.max_download_rate))
    session.set_upload_rate_limit(int(args.max_upload_rate))
    session.listen_on(args.port, args.port + 10)
    session.set_alert_mask(0xfffffff)

    if args.proxy_host != '':
        session.set_proxy(proxy_setup(args.proxy_host))

    handles = []
    for torrent in args.torrents:
        handle = session.add_torrent(session_torrents(torrent, args.save_path))
        handle.set_max_connections(60)
        handle.set_max_uploads(-1)
        handles.append(handle)

    return session, handles


def is_magneturl(torrent):
    prefixes = ["magnet:", "http://", "https://"]
    for prefix in prefixes:
        if torrent.startswith(prefix):
            return True
    return False


def session_torrents(torrent, save_path):

    torrent_dict = {"save_path": save_path, "paused": False,
                    "storage_mode": lt.storage_mode_t.storage_mode_sparse,
                    "auto_managed": True, "duplicate_is_error": True}
    if is_magneturl(torrent):
        torrent_dict["url"] = torrent
    else:
        torrent_dict["ti"] = torrent_info = lt.torrent_info(torrent)
        print("Adding {}...".format(torrent_info.name()))

        filename = os.path.join(save_path, torrent_info.name())
        fastresume = os.path.join(filename + ".fastresume")
        if os.path.isfile(fastresume):
            with open(fastresume, 'rb') as fresume:
                torrent_dict["resume_data"] = fresume.read()
        return torrent_dict


def display_info():
    session, handles = torrent_handles()
    while True:
        for handle in handles:
            handle_info(handle)


def b2kb(size):
    kb = size / 10**3
    return "{:.2f} KB".format(kb)


def b2mb(size):
    mb = size / 10**6
    return "{:.2f} MB".format(mb)


def handle_info(handle):
    # torrent_details = ["name", "total_size", "metadata", "files",
    #                    "creator", "creation_date", "trackers"]
    os.system("clear")
    if handle.has_metadata():
        torrent_info = handle.get_torrent_info()
        name, fsize = torrent_info.name(), b2mb(torrent_info.total_size())
        status_info = "NAME: {} {}".format(name, fsize)

    status = handle.status()
    state = str(status.state)
    # if state != 'seeding':
    status_info += ('\nCompleted {:.2%} download  \nTotal downloaded: {} '
                    'peers: {} \n'.format(status.progress,
                                          b2mb(status.total_done),
                                          status.num_peers))

    transfer_params = [status.download_rate, status.total_download,
                       status.upload_rate, status.total_upload]

    status_info += ('\ndownload: {0}/s ({1})  upload: {2}/s ({3})\n'
                    ' '.format(*(map(b2kb, transfer_params))))
    print(status_info)
    print(state.upper())
    if handle.get_download_queue():
        print(handle.get_download_queue())
    sleep(1)


# def main():

#     alerts = []
#     display_info()

#     while True:

#         while 1:
#             a = ses.pop_alert()
#             if not a:
#                 break
#             alerts.append(a)

#         if len(alerts) > 8:
#             alerts = alerts[-8:]

#         for a in alerts:
#             if isinstance(a, str):
#                 write_line(console, a + '\n')
#             else:
#                 write_line(console, a.message() + '\n')

#         c = console.sleep_and_input(0.5)

#         if not c:
#             continue

#         elif c == 'r':
#             for h in handles:
#                 h.force_reannounce()
#         elif c == 'q':
#             raise SystemExit
#         elif c == 'p':
#             for h in handles:
#                 h.pause()
#         elif c == 'u':
#             for h in handles:
#                 h.resume()

#     ses.pause()
#     for h in handles:
#         if not h.is_valid() or not h.has_metadata():
#             continue
#         data = lt.bencode(h.write_resume_data())
#         filename = path.join(
#             args.save_path, h.get_torrent_info().name() + '.fastresume')
#         with open(filename, 'wb') as fresume:
#             fresume.write(data)


if __name__ == "__main__":
    display_info()
    # main()


# def append_out(args):
#     cond, ok = args
#     if cond:
#         return ok
#     return "."

# def print_peer_info(console, peers):

#     out = (' down    (total )   up     (total )  q  r flags'
#            '   block progress  client\n')

#     for p in peers:
#         peer_params = [p.down_speed, p.total_download,
#                        p.up_speed, p.total_upload]

#         out += "{}/s {} {}/s {}".format(*map(add_suffix, peer_params))
#         out += '{:2} {:2}'.format(p.download_queue_length,
#                                   p.upload_queue_length)

#         if p.flags:
#             peer_items = [[peer_info.interesting, "I"],
#                           [peer_info.choked, "C"],
#                           [peer_info.remote_interested, "i"],
#                           [peer_info.remote_choked, "c"],
#                           [peer_info.supports_extensions, "e"]]
#             out += map(append_out, peer_items)

#             if lt.peer_info.local_connection:
#                 out += 'l'
#             else:
#                 out += 'r'
#         out += ' '

#         if p.downloading_piece_index >= 0:
#             assert(p.downloading_progress <= p.downloading_total)
#             out += progress_bar(float(p.downloading_progress) /
#                                 p.downloading_total, 15)
#         else:
#             out += progress_bar(0, 15)
#         out += ' '

#         if p.flags:
#             if lt.peer_info.handshake:
#                 id = 'waiting for handshake'
#             elif lt.peer_info.connecting:
#                 id = 'connecting to peer'
#             elif lt.peer_info.queued:
#                 id = 'queued'
#         else:
#             id = p.client

#         out += '{}\n'.format(id[:10])

#     write_line(console, out)


# def print_download_queue(console, download_queue):

#     out = ""
#     state_dict = {1: "-", 2: "=", 3: "#"}
#     for e in download_queue:
#         out += '%4d: [' % e['piece_index']
#         for block in e['blocks']:
#             out += state_dict.get(block['state'], " ")
#         out += ']\n'
#     write_line(console, out)
