Deploying
=========

0. Make sure you've merged all the pull requests you care to include in this release and ensure you're on the `master` branch.

    ```
    git checkout master
    ```

1. Use `bumpversion` to increment the version number. This will generate a tag and a commit.

    ```
    bumpversion minor
    ```

2. Push the tag and commit to GitHub so everyone can see it.

    ```
    git push origin master
    ```

3. Pushing the tag will trigger a GitHub Action process that will send the tag to pypi.

    ```
    git push --tags
    ```

4. Done!
