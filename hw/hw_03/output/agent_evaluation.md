# Agent Evaluation — Problem 4

Christopher's own assessment of the product-identify agent's performance
against the four test images. Raw run data lives in
`output/identify_product.json`; the technical writeup of how the agent works
is in `output/harness.md`. This file is judgment, in his own words, not a
restatement of either.

## What it got right

I like how it separately judges text-based queries (the catalog)and then if the text plausibly matches will move onto path B - checking the narrowed list of images. 

The things it matches correctly showed some judgement - like using explicit product category and sleeve length to cross things off.

## What it got wrong, or didn't handle

It doesn't like some images - Claude told me that's Azure content moderation thinking the shields and crests are military or something bad - so I built a manual workaround to tell the agent what those things are and catalog them correctly. I tried to make it iterate to get around this but it gave up, thinking it shouldn't be trying to chop down safety blocks (as informed by the Harness, which is good I guess). It also got stuck on the "Balenciaga" image maybe because content restrictions. 


## Untested or uncertain

I don't love that the text-based calls aren't double checked. In real production, I would evaluate if I have the tool-call bandwidth to check more images. 

We also did not get to test images that are definitely a product but may not match to our sample images. We don't know if match:null works.

## Verdict

Spot-checking these, I feel good about what it found. I mainly am concerned about the false positives for content restrictions, as those add manual review in and defeat a lot of the purpose. I would build more robust handling if this happens with more images.

# Problem 7 — Ad Effectiveness Evaluation

Christopher's own assessment of the ad-effectiveness ability, judged against
`data/videos/ad_humble.mp4` for both `profiles/profile_student.json` (Maya
Chen) and `profiles/profile_parent.json` (David Chen). Raw run data lives in
`output/ad_effectiveness.json`; the technical writeup (category design,
video-frame approach) is in `output/harness.md`. This file is judgment, in
his own words, not a restatement of either.

## What it got right

I agree with the justification that the video may be appealing to the parent
(David) — it does show some networking, some togetherness, some social
belonging. But I don't think it's something the parent would quite
understand, and the agent picked up on that gap. It also profiled him as
wanting crewnecks and quarter-zips instead of streetwear, which I thought was
funny and on point.

## What it got wrong, or didn't handle

Both Maya and David landed on "medium" effectiveness, and I don't think
that's quite right — Maya definitely understands the joke (the Kendrick
Lamar reference) better than David does, so their actual engagement should
differ more than the label shows. If you just looked at the effectiveness
score, some of that nuance would be lost. The reasoning itself was good, but
the single "medium" label for both didn't capture the gap between them.

## Untested or uncertain

Maybe we need a more nuanced scoring scale — not just high/medium/low, but
something that can separate "medium for different reasons" cases like this
one. "Medium" is kind of a fair catch-all here, but it might be a little
corny/lossy compared to what the reasoning actually shows.

## Verdict

Overall, I'm impressed.
