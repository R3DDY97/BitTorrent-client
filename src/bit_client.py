#!/usr/bin/env python3

import os
import argparse
from select import select
from time import sleep
import libtorrent as lt
from utils import (add_suffix, progress_bar)


from unixconsole import UnixConsole
console = UnixConsole()


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('torrents', nargs='*')

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


def process_arguments():
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
    hostname, port = proxy_host.split(":")
    proxy_settings.hostname, proxy_settings.port = hostname, int(port)
    return proxy_settings


def is_magneturl(torrent):
    url_prefix = ["magnet:", "http://", "https://"]
    for prefix in url_prefix:
        if torrent.startswith(prefix):
            return True
    return False


def append_out(args):
    cond, ok = args
    if cond:
        return ok
    return "."


def print_peer_info(console, peers):

    out = (' down    (total )   up     (total )  ip client q  r flags'
           '   block progress  client\n')

    for p in peers:
        peer_params = [p.down_speed, p.total_download,
                       p.up_speed, p.total_upload, p.ip, p.client]

        out += "{}/s {} {}/s {} {} {}".format(*map(add_suffix, peer_params))
        out += '{:2} {:2}'.format(p.download_queue_length,
                                  p.upload_queue_length)

        if p.flags:
            peer_items = [[lt.peer_info.interesting, "I"],
                          [lt.peer_info.choked, "C"],
                          [lt.peer_info.remote_interested, "i"],
                          [lt.peer_info.remote_choked, "c"],
                          [lt.peer_info.supports_extensions, "e"]]
            out += " ".join(map(append_out, peer_items))

            if lt.peer_info.local_connection:
                out += 'l '
            else:
                out += 'r '

        if p.downloading_piece_index >= 0:
            assert(p.downloading_progress <= p.downloading_total)
            out += progress_bar(float(p.downloading_progress) /
                                p.downloading_total, 15)
        else:
            out += progress_bar(0, 15)
        out += ' '

        if p.flags:
            if lt.peer_info.handshake:
                id = 'waiting for handshake'
            elif lt.peer_info.connecting:
                id = 'connecting to peer'
            elif lt.peer_info.queued:
                id = 'queued'
        else:
            id = p.client

        out += '{}\n'.format(id[:10])
    print(out)


def print_download_queue(console, download_queue):

    out = ""
    state_dict = {1: "-", 2: "=", 3: "#"}
    for e in download_queue:
        out += '%4d: [' % e['piece_index']
        for block in e['blocks']:
            out += state_dict.get(block['state'], " ")
        out += ']\n'


def torrent_properties(torrent, save_path):
    torrent_dict = {"save_path": save_path, "paused": False,
                    "storage_mode": lt.storage_mode_t.storage_mode_sparse,
                    "auto_managed": True, "duplicate_is_error": True}

    if is_magneturl(torrent):
        torrent_dict["url"] = torrent
    else:
        torrent_dict["ti"] = info = lt.torrent_info(torrent)
        print("Adding {}...".format(info.name()))

    fastresume = os.path.join(save_path, info.name(), ".fastresume")
    if os.path.isfile(fastresume):
        with open(fastresume, 'rb') as fresume:
            torrent_dict["resume_data"] = fresume.read()

    return torrent_dict


def torrent_handles():
    args = process_arguments()
    session = lt.session()
    settings = lt.session_settings()
    settings.user_agent = 'python_client/{}'.format(lt.version)

    session.set_download_rate_limit(int(args.max_download_rate))
    session.set_upload_rate_limit(int(args.max_upload_rate))
    session.listen_on(args.port, args.port + 10)
    session.set_settings(settings)
    session.set_alert_mask(0xfffffff)

    if args.proxy_host:
        session.set_proxy(proxy_setup(args.proxy_host))

    torrent_handles = []

    for torrent in args.torrents:
        handle = session.add_torrent(
            torrent_properties(torrent, args.save_path))
        handle.set_max_connections(60)
        handle.set_max_uploads(-1)
        torrent_handles.append(handle)

    return args.save_path, session, torrent_handles


def pause_torrents(handles, save_path):
    for handle in handles:
        if not handle.is_valid() or not handle.has_metadata():
            pass
        data = lt.bencode(handle.write_resume_data())
        filename = os.path.join(
            save_path + handle.get_torrent_info().name() + '.fastresume')
        with open(filename, 'wb') as fresume:
            fresume.write(data)


def user_action(handles):
    action_dict = {"p": lambda: [handle.pause() for handle in handles],
                   "u": lambda: [handle.resume() for handle in handles],
                   "r": lambda: [handle.force_reannounce() for handle in handles],
                   "q": lambda: SystemExit}
    fd = os.sys.stdin
    read, _, _ = select([fd.fileno()], [], [], 1)
    if read and fd.read(1) in action_dict:
        action_dict[fd.read(1)]()
    return


def main():

    save_path, session, handles = torrent_handles()
    alerts = []

    while True:

        for handle in handles:
            os.system("clear")
            # print(r'(q)uit), (p)ause), (u)npause), (r)eannounce\n')
            print("Enter CTRL+C to stop\n")
            if handle.has_metadata():
                # print_peer_info(console, handle.get_peer_info())
                # print_download_queue(console, handle.get_download_queue())

                name = handle.get_torrent_info().name() or "-"
                file_size = handle.get_torrent_info().total_size()//10**6

                heading = 'NAME:- {}  SIZE:{} MB\n'.format(name, file_size)
                print(heading)

            s = handle.status()
            format_list = [str(s.state), s.progress, s.total_done,
                           s.num_peers, s.num_seeds, s.distributed_copies]
            if s.state != lt.torrent_status.seeding:
                to_print = ("staus:- {}  progress: {} \ntotal downloaded: {}"
                            "Bytes \npeers: {} seeds: {} distributed copies:{}".format(*format_list))

                print(to_print, end='\r', sep='\r')

            transfer_params = [s.download_rate, s.total_download,
                               s.upload_rate, s.total_upload]

            to_print = ('download: {0}/s ({1})  upload: {2}/s ({3})'
                        ' '.format(*map(add_suffix, transfer_params)))
            print(to_print, end='\r', sep='\r')
            sleep(1)
            # user_action(handles)

    session.pause()
    pause_torrents(handles, save_path)


if __name__ == "__main__":
    main()
