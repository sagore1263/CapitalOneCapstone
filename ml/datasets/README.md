# Dataset Setup (Git LFS Required)

The training and testing datasets in this directory are stored using **Git LFS**.
If you cloned the repo before Git LFS was installed, the dataset files will appear as small pointer files instead of the real CSV data.

### 1. Install Git LFS

Install **Git LFS**:

Mac:

```
brew install git-lfs
```

Then initialize it:

```
git lfs install
```

### 2. Download the datasets

From the root of the repository run:

```
git lfs pull
```

This will download the actual dataset files:

```
ml/datasets/fraudTrain.csv
ml/datasets/fraudTest.csv
```

### 3. Verify

You can verify the datasets are tracked correctly with:

```
git lfs ls-files
```

### Notes

* If you cloned the repo **after Git LFS was enabled**, the datasets should download automatically.
* If the CSV files contain only a few lines beginning with `version https://git-lfs.github.com/spec/v1`, run `git lfs pull` to fetch the real files.
