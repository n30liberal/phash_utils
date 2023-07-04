This is all hacky and proof of concept, and not done well at all.

These independent scripts are meant to help use stashapps database data to help remove perfectly matched phashes in a more friendly way.
(their web interface is not very friendly for this)

## Usage

fill out the user_config.py file with your information.

1. remove_dupes.py
    - This reads the sqlite database, and groups every file by phash
    - Then it shows you every group with more than 1 file in it, and asks you if you want to delete the files in that group.
    - Optionally, you can run the companion_server.py, and refresh it's webpage each time you get a prompt to delete a file, and it will embed the videos for you to watch and decide if you want to delete them, but you cannot do anything from the webpage other than copy the filenames to your clipboard, or by clicking the phash at the top and that will append it to your blacklisted_phashes.txt file.

2.  generate_missing_image_phashes.py
    - Here we can use the stash database to see which images we have in our system, and then it can generate a phash for each image.
    - ~~The outputted csv has no current use, but in the future we will add the image phashes into our sqlite database, and then we can use that remove images with shared phashes, the same way we do with videos.~~
    - You can now scan for duplicate images *after* running this py file. Just be sure to run remove_dupes.py without the --rebuild-database param.
    - You also need to pass --allowed-media-types image
    - Currently it generates 2 files, phashes.csv, which gives us file_id,phash, and then phashed_file_ids.txt which tells the script which images have already been phashed, so it can skip them. This can ideally be done with just the phashes.csv, and it did for a moment, but I broke something and was too lazy to figure out what, so did this as a quick fix.


## final notes

These are all real hacky, and I only got them to a usable state for myself. Theres so many ways to improve them, and will get to it eventually.
Ultimately, I also dont want the companion server, I want this all packaged with a single script using CustomTkinter for the interface.

Also, I'd also like to be able to group phashes by non-exact matches, but math is not my strong suit, so that's on the back burner.

Ultimately I think I've laid the ground work for a single implementation that can do all of this, and I'll get to it eventually, but for now, this is what I have.
