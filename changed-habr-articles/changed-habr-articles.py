import os
import subprocess
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from transliterate import translit
from PIL import Image
from io import BytesIO
import sys

# Constants
REPO_PATH = './website'
CONTENT_PATH = os.path.join(REPO_PATH, 'content/ru/_articles')
IMG_PATH = os.path.join(REPO_PATH, 'public/img/articles')
GITHUB_REPO_URL = 'git@github.com:wirenboard/website.git'
HABR_RSS_FEED_URL = 'https://habr.com/ru/rss/companies/wirenboard/articles/?fl=ru'
EXCLUDE_KEYWORDS = ["интервью", "выставка", "репортаж", "конференция", "wbce"]
EXCLUDE_AUTHORS = ["lavritech", "another_author"]  # List of excluded authors

# Flags
dry_run = "--dry-run" in sys.argv
debug = "--debug" in sys.argv

def log(message):
    """Standardized logging function for clean output."""
    print(f"> {message}")

def debug_log(message):
    """Log debug messages."""
    if debug:
        print(f"[DEBUG] {message}")

def emulate_log(message):
    """Log messages during dry run mode."""
    print(f"[EMULATION] {message}")

def transliterate_filename(title):
    """Transliterate and clean title for filename compatibility."""
    translit_title = translit(title, 'ru', reversed=True).lower()
    clean_title = "".join([char if char.isalnum() or char == " " else "" for char in translit_title])
    words = clean_title.split()

    # Limit to 7 words
    filename = "_".join(words[:7])

    # Check for existing filenames
    base_filename = filename
    counter = 1
    while os.path.exists(os.path.join(CONTENT_PATH, f"{filename}.md")):
        filename = f"{base_filename}_{counter}"
        counter += 1

    return filename

def run_command(command):
    """Run a command with error handling."""
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        log(f"Error running command {' '.join(command)}: {e}")
        sys.exit(1)

def clone_or_update_repo():
    """Clone repo if it doesn't exist, else pull latest and clean."""
    if not os.path.exists(REPO_PATH):
        log("Cloning repository...")
        run_command(["git", "clone", GITHUB_REPO_URL, REPO_PATH])
    else:
        log("Repository already exists. Pulling latest changes and cleaning...")
        run_command(["git", "-C", REPO_PATH, "checkout", "main"])
        run_command(["git", "-C", REPO_PATH, "pull"])
        run_command(["git", "-C", REPO_PATH, "clean", "-fd"])

def fetch_habr_articles():
    """Fetch articles from Habr RSS feed and filter based on criteria."""
    response = requests.get(HABR_RSS_FEED_URL)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    articles, excluded = [], []

    for item in root.findall(".//item"):
        title = item.find("title").text or ""
        description = item.find("description").text or ""
        creator = item.find("{http://purl.org/dc/elements/1.1/}creator").text or ""
        categories = [cat.text for cat in item.findall("category") if cat.text]
        pub_date = item.find("pubDate").text or ""
        date_formatted = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z").strftime("%Y-%m-%d")

        exclusion_reason = None
        if any(author.lower() in creator.lower() for author in EXCLUDE_AUTHORS):
            exclusion_reason = "author excluded"
        elif any(keyword in title.lower() + description.lower() for keyword in EXCLUDE_KEYWORDS):
            exclusion_reason = "keyword in title/description"
        elif any(keyword in category.lower() for category in categories for keyword in EXCLUDE_KEYWORDS):
            exclusion_reason = "keyword in category"

        if exclusion_reason:
            excluded.append(f"{item.find('link').text.split('?')[0]} — exclusion reason: {exclusion_reason}")
        else:
            articles.append({
                "title": title,
                "link": item.find("link").text.split('?')[0],
                "image_url": extract_image_url(description),
                "date": date_formatted
            })

    log(f"Excluded Habr articles: {len(excluded)}")
    for article in excluded:
        debug_log(article)

    return articles

def fetch_github_articles():
    """Fetch existing article URLs from the GitHub repository to avoid duplicates."""
    github_articles = []
    try:
        result = subprocess.run(
            ["grep", "-hr", "^url: ", CONTENT_PATH],
            text=True, capture_output=True, check=True
        )
        for line in result.stdout.splitlines():
            _, url = line.split("url: ")
            github_articles.append(url.strip())
        log(f"Fetched {len(github_articles)} existing articles from GitHub.")
    except subprocess.CalledProcessError as e:
        log(f"Error fetching articles from GitHub: {e}")
        return []
    return github_articles

def extract_image_url(description):
    """Extract image URL from the description HTML."""
    if "<img src=" in description:
        start = description.find("<img src=") + len("<img src=\"")
        end = description.find("\"", start)
        return description[start:end]
    return None

def save_image(image_url, filename):
    """Download and save image as a 500px width .webp file."""
    try:
        response = requests.get(image_url)
        response.raise_for_status()  # Check for request errors
        image = Image.open(BytesIO(response.content))
        image = image.convert("RGB")
        image.thumbnail((500, image.height), Image.LANCZOS)  # Use LANCZOS for high-quality downsampling
        image_path = os.path.join(IMG_PATH, f"{filename}.webp")
        image.save(image_path, "webp")
        debug_log(f"Image saved: {image_path}")
        return image_path
    except Exception as e:
        log(f"Failed to save image {image_url}: {e}")
        return None

def create_markdown_file(title, link, filename, date):
    """Create markdown file for article."""
    md_content = f"""---
title: "{title}"
url: {link}
cover: /img/articles/{filename}.webp
date: {date}
category: IMPORTED_SELECT_CATEGORY
---"""

    md_file_path = os.path.join(CONTENT_PATH, f"{filename}.md")
    with open(md_file_path, "w") as file:
        file.write(md_content)
    debug_log(f"Markdown file created: {md_file_path}")
    return md_file_path

def delete_existing_branch(branch_name):
    """Delete existing branch if it exists."""
    run_command(["git", "-C", REPO_PATH, "branch", "-D", branch_name])
    log(f"Deleted branch '{branch_name}'.")

def create_branch(branch_name):
    """Create a new branch."""
    run_command(["git", "-C", REPO_PATH, "checkout", "-b", branch_name])
    log(f"Switched to new branch '{branch_name}'.")

def commit_changes(dry_run, commit_message):
    """Commit the changes to the repository."""
    if dry_run:
        emulate_log(f"Committing with message: '{commit_message}'")
    else:
        run_command(["git", "-C", REPO_PATH, "commit", "-m", commit_message])
        debug_log(f"[DEBUG] Committed with message: '{commit_message}'")

def push_changes(branch_name, dry_run):
    """Push the changes to the remote repository."""
    if dry_run:
        emulate_log(f"Pushing branch {branch_name}")
    else:
        run_command(["git", "-C", REPO_PATH, "push", "--set-upstream", "origin", branch_name])
        debug_log(f"[DEBUG] Pushed branch '{branch_name}' to remote.")

import os

def create_pull_request(commit_message, pr_body, dry_run):
    """Create a pull request on GitHub."""
    if dry_run:
        emulate_log(f"Creating pull request with title: '{commit_message}'")
    else:
        try:
            # Change of working directory to repo_path to execute the GH PR Create command
            original_dir = os.getcwd()  # Save the current directory
            os.chdir(REPO_PATH)         # Go to the Directory of the Repository
            run_command(["gh", "pr", "create", "--title", commit_message, "--body", pr_body])
            debug_log(f"[DEBUG] Created pull request with title: '{commit_message}'.")
        except subprocess.CalledProcessError as e:
            log(f"Error running command for pull request creation: {e}")
        finally:
            os.chdir(original_dir)      # Return to the source directory



def commit_and_push_changes(created_files, dry_run=False):
    """Commit and push changes to the repository, or emulate if dry_run is True."""
    branch_name = f"feature/add-new-articles-{datetime.now().strftime('%Y%m%d')}"

    # Check if the branch already exists
    result = subprocess.run(
        ["git", "-C", REPO_PATH, "branch"],
        text=True, capture_output=True, check=True
    )
    existing_branches = result.stdout.splitlines()
    if any(branch_name in branch for branch in existing_branches):
        log(f"Branch '{branch_name}' already exists. Deleting it...")
        delete_existing_branch(branch_name)

    if dry_run:
        emulate_log(f"Creating branch {branch_name}")
    else:
        create_branch(branch_name)

    commit_message = "Add new articles from Habr"
    pr_body = (
        "Automatically created pull request with new articles. "
        "Please replace `IMPORTED_SELECT_CATEGORY` with actual categories. "
        "Category file: https://github.com/wirenboard/website/blob/main/common/article_categories.ts"
    )

    for md_file, img_file in created_files:
        # Relative ways for Git Add
        md_file_rel = os.path.relpath(md_file, REPO_PATH)
        img_file_rel = os.path.relpath(img_file, REPO_PATH)

        # We check if there are files before adding
        if not os.path.exists(md_file) or not os.path.exists(img_file):
            log(f"Warning: File(s) not found for commit: {md_file}, {img_file}")
            continue

        if dry_run:
            emulate_log(f"Adding file: {md_file_rel}")
            emulate_log(f"Adding file: {img_file_rel}")
        else:
            run_command(["git", "-C", REPO_PATH, "add", md_file_rel, img_file_rel])

    commit_changes(dry_run, commit_message)
    push_changes(branch_name, dry_run)
    create_pull_request(commit_message, pr_body, dry_run)



def main():
    clone_or_update_repo()
    habr_articles = fetch_habr_articles()
    github_articles = fetch_github_articles()
    new_articles = [article for article in habr_articles if article["link"] not in github_articles]

    if not new_articles:
        log("No new articles to process.")
        return

    log(f"Found {len(new_articles)} new articles to process.")
    created_files = []
    for article in new_articles:
        filename = transliterate_filename(article["title"])
        md_file = create_markdown_file(article["title"], article["link"], filename, article["date"])
        img_file = save_image(article["image_url"], filename)
        created_files.append((md_file, img_file))

    commit_and_push_changes(created_files, dry_run=dry_run)

if __name__ == "__main__":
    main()
