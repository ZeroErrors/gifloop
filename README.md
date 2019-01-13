GifLoop
----
A tool to help make a nice looping gif.

_Requires ffmpeg (Tested with version 4.1)_


Usage
----
```
usage: gifloop.py [-h] [-o file] [-p file] [-H pixels] [-f fps] [-l seconds]
                  [-t {ssim,psnr}] [-r file] [-d dir] [-A pixels] [-F fps]
                  [--skip-frames frames] [--max-frames frames] [--processes n]
                  [-c] [-v]
                  file

positional arguments:
  file                  The input file to process

optional arguments:
  -h, --help            show this help message and exit
  -o file, --output file
                        The file to store the output gif
  -p file, --palette file
                        The file to store the output gif palette
  -H pixels, --height pixels
                        The height of the output gif
  -f fps, --fps fps     The frame rate of the output gif
  -l seconds, --length seconds
                        The maximum length of the output gif
  -t {ssim,psnr}, --analyze-type {ssim,psnr}
                        The algorithm to use when analyzing frames
  -r file, --result file
                        The file to store the frame analyze results
  -d dir, --frames-dir dir
                        The directory to store the exported frames
  -A pixels, --analyze-height pixels
                        The height of the exported frames to analyze
  -F fps, --analyze-fps fps
                        The frame rate of the exported frames to analyze
  --skip-frames frames  The number of frames to skip when analyze frames
  --max-frames frames   The maximum number of frames to analyze
  --processes n         The number of parallel task to run when analyzing
                        frames
  -c, --clean           Cleans up the files when finished
  -v, --verbose         Increase the logging verbosity
```


TODO
----
- Add binary search frame comparison (May improve speed?)
- Use frame time stamps instead of indexes so that if the analyze frame rate is changed the existing 'frames' and 'results.db' can still be used 
- Allow exporting more than one loop and/or to select the loop to export from the results
- Improve update_progress with rate and ETA
- Add extra frame comparison options
- UI to visually see the loop before exporting

_These are just a few ideas that would improve this tool but unlikely I will have time to implement them_
