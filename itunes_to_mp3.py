
import eyed3
import os
from libpytunes import Library
from multiprocessing import Queue, Process
from pydub import AudioSegment
from mutagen import File
from PIL import Image

from resizeimage import resizeimage
from threading import Thread

OUTDIR = '/Users/ruu/Desktop/out'


def get_album_key(song_object):
    return '{artist} - {album}'.format(artist=song_object.album_artist, album=song_object.album)


def get_full_path_from_song(song_object):
    return '/{loc}'.format(loc=song_object.location)


def process_album(album_artist, album, songs):
    album_folder = '{base_dir}/{album_artist}/{album}'.format(
        base_dir=OUTDIR, album_artist=album_artist, album=album
    )
    if not os.path.exists(album_folder):
        os.makedirs(album_folder)

    print('{album_artist} > {album}'.format(album_artist=album_artist, album=album))

    snagged_artwork = None
    converted_mp3s = []

    for song in songs:
        if snagged_artwork is None:
            mut = File(get_full_path_from_song(song))
            if 'covr' in mut.tags:
                if mut.tags['covr']:
                    art = mut.tags['covr'][0]
                    extn = 'jpg' if art.imageformat == 13 else 'png'
                    with open(
                            '{album_folder}/artwork.{extn}'.format(album_folder=album_folder, extn=extn), 'wb'
                    ) as f:
                        f.write(art)
                        snagged_artwork = extn

        segment = AudioSegment.from_file(get_full_path_from_song(song))

        mp3_path = '{album_folder}/{track_num}. {title}.mp3'.format(
            album_folder=album_folder,
            track_num=song.track_number,
            title=song.name.replace('/', '-')
        )
        converted_mp3s.append(mp3_path)

        segment.export(
            mp3_path,
            format='mp3',
            parameters=["-q:a", "0"],
            id3v2_version='3',
            tags={
                'artist': song.artist,
                'album_artist': song.album_artist,
                'album': song.album,
                'disk': song.disc_number,
                'title': song.name,
                'track': song.track_number
            }
        )

    if snagged_artwork is not None:
        extracted = '{album_folder}/artwork.{extn}'.format(album_folder=album_folder, extn=snagged_artwork)
        processed = '{album_folder}/artwork_processed.jpg'.format(album_folder=album_folder)

        with open(extracted, 'rb') as f:
            artwork = Image.open(f)
            artwork = resizeimage.resize_thumbnail(artwork, [400, 400])
            artwork.save(processed)

        for mp3_path in converted_mp3s:
            id3 = eyed3.load(mp3_path)
            id3.tag.images.set(
                3,
                open(processed, 'rb').read(),
                'image/jpeg'
            )
            id3.tag.save()

        os.remove(extracted)
        os.remove(processed)


def process_enclosure(q):
    while True:
        album_artist, album, songs = q.get()
        process_album(album_artist, album, songs)


def run_export():
    library = Library('/Users/ruu/Music/iTunes/iTunes Music Library.xml')

    library_data = {}

    for song_id, song_data in library.songs.items():
        if song_data.album_artist not in library_data:
            library_data[song_data.album_artist] = {}

        if song_data.album not in library_data[song_data.album_artist]:
            library_data[song_data.album_artist][song_data.album] = []

        library_data[song_data.album_artist][song_data.album].append(song_data)

    for i in range(8):
        Process(target=process_enclosure, args=(album_queue, )).start()

    for album_artist, albums in library_data.items():
        for album, songs in albums.items():
            album_queue.put((album_artist, album, songs, ))

if __name__ == '__main__':
    album_queue = Queue()
    run_export()
    # album_queue.join()
