This is all hacky and proof of concept, and not done well at all.

These independent scripts are meant to help use stashapps database data to help remove perfectly matched phashes in a more friendly way.
(their web interface is not very friendly for this)

Only works with exact match phashes! I still have to figure out how to do the distance stuff for close matches.

## WARNING
remove_dupes.py - when its asking if you want to remove a file, it assumes no input == yes, so you actually need to put n for no

remove_dupes.py - --auto-delete, will delete without input if it determines the first frame is a good enough match (mse threshold) for both files. (both being biggest_file, and smaller_file)

remove_dupes.py - it will actually only *really* delete files if you pass --direct-delete, otherwise it moves the file to the specified trash directory

## Usage

fill out the user_config.py file with your information.

1. remove_dupes.py
    - This reads the sqlite database, and groups every file by phash
    - Then it shows you every group with more than 1 file in it, and asks you if you want to delete the files in that group. A file at a time.
    - Optionally, you can run file_comparison_gui.py, with --output-to-window, and it will show a poorly designed, nowhere near finished window that shows the first frame for each video.
    - It assumes you have sudo installed on windows to kill the previous instance each time its called (yes i know, very bad)

2.  generate_missing_image_phashes.py
    - Here we can use the stash database to see which images we have in our system, and then it can generate a phash for each image.
    - ~~The outputted csv has no current use, but in the future we will add the image phashes into our sqlite database, and then we can use that remove images with shared phashes, the same way we do with videos.~~
    - You can now scan for duplicate images *after* running this py file. Just be sure to run remove_dupes.py without the --rebuild-database param, before generating your phashes.
    - Each rebuild from remove_dupes.py destroys the injected phashes from this.
    - You also need to pass --allowed-media-types image
    - Currently it generates 2 files, phashes.csv, which gives us file_id,phash, and then phashed_file_ids.txt which tells the script which images have already been phashed, so it can skip them. This can ideally be done with just the phashes.csv, and it did for a moment, but I broke something and was too lazy to figure out what, so did this as a quick fix.


## final notes

These are all real hacky, and I only got them to a usable state for myself. Theres so many ways to improve them, and will get to it eventually.
Ultimately, I don't want a separate gui app, this solution isnt good.

Also, I'd also like to be able to group phashes by non-exact matches, but math is not my strong suit, so that's on the back burner.

Ultimately I think I've laid the ground work for a single implementation that can do all of this, and I'll get to it eventually, but for now, this is what I have.
