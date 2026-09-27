# review-router launch reel: 30 seconds, built in code

A 30-second motion-graphics video for review-router, made with [Remotion](https://www.remotion.dev). The soundtrack is synthesized in Python from the same timing file, so no samples or stock music are used.

```sh
npm install
npm run studio   # scrub the timeline in a browser
npm run render   # regenerate music, then out/review-router.mp4 (1080p)
npm run poster   # out/poster.png key art
```

## One timing file

[src/cues.json](src/cues.json) holds every time in the video. The scenes read it, and [scripts/music.py](scripts/music.py) reads it to place every kick, riser and UI sound. Move a cue and the picture and the sound move together.

The video opens on a 0.6-second hold of the key art, because X and LinkedIn pick an early frame as the thumbnail.

## The six scenes

1. Your AI reviewer re-reads the whole pull request, every push.
2. A path rule skips by filename, and waves 13 CVE fixes through.
3. Read the diff instead: 10 yes/no checks, asked at once.
4. The fork: every CVE fix goes to full review.
5. The numbers from the public benchmark.
6. The one-line install.

Every number on screen comes from [the benchmark write-up](../results/2026-09-27-review-routing-public.md). The check scores in scene 3 are Jev's real answers on the `validation-removed` test diff.
