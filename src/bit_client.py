#!/usr/bin/env python3

from os import (sys, path)
import argparse
import libtorrent as lt
from utils import (add_suffix, progress_bar)


if sys.platform == 'win32':
    from windowsconsole import WindowsConsole
    console = WindowsConsole()
else:
    from unixconsole import UnixConsole
    console = UnixConsole()


def load_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('torrent')

    parser.add_argument('-p', '--port', type='int', default=6881,
                        help='set listening port')

    parser.add_argument('-d', '--max-download-rate', type='float', default=0,
                        help='the maximum download rate given in kB/s.'
                        '0 means infinite.')

    parser.add_argument('-u', '--max-upload-rate', type='float', default=0,
                        help='the maximum upload rate given in kB/s.'
                        '0 means infinite.')

    parser.add_argument('-s', '--save-path', type='string', default=".",
                        help='the path to save the downloaded file/folder')

    parser.add_argument('-a', '--allocation-mode', type='string',
                        help='sets mode for allocating the downloaded files'
                        'Possible args are [full | compact]',
                        default='compact')

    parser.add_argument('-r', '--proxy-host', type='string',
                        help="sets HTTP proxy host and port"
                        "(separated by :)", default='')

    args = parser.parse_args()
    return args


def write_line(console, line):
    console.write(line)


def append_out(args):
    cond, ok = args
    if cond:
        return ok
    return "."


def print_peer_info(console, peers):

    out = (' down    (total )   up     (total )  q  r flags'
           '   block progress  client\n')

    for p in peers:
        peer_params = [p.down_speed, p.total_download,
                       p.up_speed, p.total_upload]

        out += "{}/s {} {}/s {}".format(*map(add_suffix, peer_params))
        out += '{:2} {:2}'.format(p.download_queue_length,
                                  p.upload_queue_length)

        if p.flags:
            peer_items = [[peer_info.interesting, "I"],
                          [peer_info.choked, "C"],
                          [peer_info.remote_interested, "i"],
                          [peer_info.remote_choked, "c"],
                          [peer_info.supports_extensions, "e"]]
            out += map(append_out, peer_items)

            if lt.peer_info.local_connection:
                out += 'l'
            else:
                out += 'r'
        out += ' '

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

    write_line(console, out)


def print_download_queue(console, download_queue):

    out = ""
    state_dict = {1: "-", 2: "=", 3: "#"}
    for e in download_queue:
        out += '%4d: [' % e['piece_index']
        for block in e['blocks']:
            out += state_dict.get(block['state'], " ")
        out += ']\n'
    write_line(console, out)


def main():

    args = load_arguments()

    args.max_upload_rate *= 1000
    args.max_download_rate *= 1000
    compact_allocation = args.allocation_mode == 'compact'

    settings = lt.session_settings()
    settings.user_agent = 'python_client/' + lt.version

    if args.port < 0 or args.port > 65525:
        args.port = 6881

    if args.max_upload_rate <= 0:
        args.max_upload_rate = -1

    if args.max_download_rate <= 0:
        args.max_download_rate = -1

    ses = lt.session()
    ses.set_download_rate_limit(int(args.max_download_rate))
    ses.set_upload_rate_limit(int(args.max_upload_rate))
    ses.listen_on(args.port, args.port + 10)
    ses.set_settings(settings)
    ses.set_alert_mask(0xfffffff)

    if args.proxy_host != '':
        ps = lt.proxy_settings()
        ps.type = lt.proxy_type.http
        ps.hostname = args.proxy_host.split(':')[0]
        ps.port = int(args.proxy_host.split(':')[1])
        ses.set_proxy(ps)

    handles = []
    alerts = []

    for torr in args.torrent:
        atp = {}
        atp["save_path"] = args.save_path
        atp["storage_mode"] = lt.storage_mode_t.storage_mode_sparse
        atp["paused"] = False
        atp["auto_managed"] = True
        atp["duplicate_is_error"] = True

        url_starter = ["magnet:", "http://", "https://"]
        for starter in url_starter:
            if args.torrent.startswith(starter):
                atp["url"] = args.torrent
                break

        if not atp.get("url", False):
            info = lt.torrent_info(torr)
            print("Adding {}...".format(info.name()))
            atp["ti"] = info

            filename = args.save_path, info.name()
            fastresume = path.join(filename + ".fastresume")
            if path.isfile(fastresume):
                with open(fastresume, 'rb') as fresume:
                    atp["resume_data"] = fresume.read()

        h = ses.add_torrent(atp)

        handles.append(h)

        h.set_max_connections(60)
        h.set_max_uploads(-1)

    alive = True
    while alive:
        console.clear()

        out = ''

        for h in handles:
            if h.has_metadata():
                name = h.get_torrent_info().name()[:40]
            else:
                name = '-'
            out += 'name: %-40s\n' % name

            s = h.status()

            if s.state != lt.torrent_status.seeding:
                state_str = ['queued ', 'checking ', 'downloading metadata ',
                             'downloading ', 'finished ', 'seeding ',
                             'allocating ', 'checking fastresume ']
                out += state_str[s.state]

                out += '%5.4f%% ' % (s.progress*100)
                out += progress_bar(s.progress, 49)

                out += ('\ntotal downloaded: {0} Bytes\n'
                        'peers: {1} seeds: {2} distributed copies: {3}'
                        '\n\n'.format(s.total_done, s.num_peers,
                                      s.num_seeds, s.distributed_copies))

            transfer_params = [s.download_rate, s.total_download,
                               s.upload_rate, s.total_upload]

            out += ('download: {0}/s ({1})  upload: {2}/s ({3})'
                    ' '.format(*map(add_suffix(transfer_params))))

            if s.state != lt.torrent_status.seeding:
                out += ('info-hash: {0}\nnext announce: {1}\ntracker: {2}'
                        '\n'.format(h.info_hash, s.next_announce,
                                    s.current_tracker))

            write_line(console, out)

            print_peer_info(console, h.get_peer_info())
            print_download_queue(console, h.get_download_queue())

            if s.state != lt.torrent_status.seeding:
                try:
                    out = '\n'
                    fp = h.file_progress()
                    ti = h.get_torrent_info()
                    for f, p in zip(ti.files(), fp):
                        out += progress_bar(p / float(f.size), 20)
                        out += ' ' + f.path + '\n'
                    write_line(console, out)
                except:
                    pass

        write_line(console, 76 * '-' + '\n')
        write_line(console, '(q)uit), (p)ause), (u)npause), (r)eannounce\n')
        write_line(console, 76 * '-' + '\n')

        while 1:
            a = ses.pop_alert()
            if not a:
                break
            alerts.append(a)

        if len(alerts) > 8:
            alerts = alerts[-8:]

        for a in alerts:
            if isinstance(a, str):
                write_line(console, a + '\n')
            else:
                write_line(console, a.message() + '\n')

        c = console.sleep_and_input(0.5)

        if not c:
            continue

        elif c == 'r':
            for h in handles:
                h.force_reannounce()
        elif c == 'q':
            alive = False
        elif c == 'p':
            for h in handles:
                h.pause()
        elif c == 'u':
            for h in handles:
                h.resume()

    ses.pause()
    for h in handles:
        if not h.is_valid() or not h.has_metadata():
            continue
        data = lt.bencode(h.write_resume_data())
        filename = path.join(
            args.save_path, h.get_torrent_info().name() + '.fastresume')
        with open(filename, 'wb') as fresume:
            fresume.write(data)


if __name__ == "__main__":
    main()
