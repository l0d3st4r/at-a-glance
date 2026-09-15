# Getting v0 online -- step by step

This gets the raw, unstyled data pipeline live at a real URL, refreshing itself
automatically. No coding needed from you for this part -- just account setup
and a few clicks.

## 1. Create a free GitHub account
Go to github.com and sign up (free tier is all you need).

## 2. Install GitHub Desktop
Go to desktop.github.com and install it. This gives you a simple app with
buttons (no command line) to get these files onto GitHub. Sign in with the
account from step 1.

## 3. Create the repository
In GitHub Desktop: File > New Repository. Name it something like
`at-a-glance`. Keep "Initialize with a README" unchecked. Pick any location
on your computer to save it. Click "Create Repository", then "Publish
repository" (top right) -- keep it Public (needed for free GitHub Pages).

## 4. Add the project files
GitHub Desktop just created an empty folder on your computer with the
repository's name. Copy every file and folder I've given you (including the
hidden `.github` folder -- your file browser may need "show hidden files"
turned on to see it, but it will still copy correctly even if you drag the
whole batch at once) into that folder.

## 5. Commit and push
Back in GitHub Desktop, you'll see all the new files listed on the left.
Type a summary like "Initial v0 pipeline" in the box at the bottom left,
click "Commit to main", then click "Push origin" at the top. That's it --
the code is now on GitHub.

## 6. Turn on GitHub Pages
On github.com, go to your repository, then Settings > Pages (left sidebar).
Under "Build and deployment" > "Source", choose **GitHub Actions** (not
"Deploy from a branch" -- this matters, the workflow file expects this
setting).

## 7. Run it for the first time
Go to the "Actions" tab on your repository. Click "Refresh matchup data and
publish" in the left list, then click the "Run workflow" button on the
right and confirm. This starts the very first real run -- and since I
couldn't test this pipeline against live data before handing it to you,
this is also our real first test.

## 8. Check the result
Click into the run that appears to watch its progress. If it finishes with
a green checkmark, go back to Settings > Pages -- it'll show your live
URL (something like `https://yourusername.github.io/at-a-glance/`). Open
it -- that's v0.

If it fails (red X), click into the failed step to see the error text, and
send it to me -- since I couldn't run this against real data beforehand,
some field names in the script may need a small fix based on what ESPN's
API actually returns. That's expected and normal for a first run, not a
sign anything is fundamentally wrong.

## After that
The workflow is already set to re-run automatically twice a day (8am and
4pm UTC) with no further action from you. You can also trigger it manually
anytime from the Actions tab the same way as step 7.
