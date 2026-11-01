# AWS Account Manager

**A Windows desktop application for managing AWS profiles and Amazon S3 files through the AWS CLI.**

Developed by **Bob Paydar**.

AWS Account Manager combines an Explorer-style file browser, image previews, text editing, and AWS command execution in one desktop interface. Users connect their own AWS accounts and work within their assigned permissions.

## Features

- **Multiple AWS profiles** with access-key configuration, SSO setup, and account verification.
- **S3 file management:** browse folders, upload multiple files, download, replace, and delete objects.
- **Seven file views:** Extra large icons, Large icons, Medium icons, Small icons, List, Details, and Tiles.
- **Large icons by default**, with image thumbnails and improved file colors.
- **Selection tools:** checkboxes, multiple selection, Select all, Select none, and Invert.
- **Image previews:** zoom, fit, actual size, pan, rotate, and save a local PNG copy.
- **Built-in UTF-8 text editor** with conditional saves to help prevent overwriting remote changes.
- **Automatic file refresh** after uploads, edits, and deletions.
- **Project save/open** for profile references, folders, view preferences, and other settings.
- **Optional encrypted login backups** protected with Windows DPAPI.
- **AWS command console** for additional services supported by the installed AWS CLI.
- **Searchable Help window** and an offline **AWS Setup Readme.txt** guide.
- **Windows build scripts** for launching the application, creating an EXE, and building an installer.

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or later, including Tcl/Tk and pip, when running from source
- AWS CLI v2
- Pillow for image thumbnails and previews
- An AWS account with appropriate permissions

The launcher checks prerequisites and installs Pillow when needed. If AWS CLI is missing, the application offers its official Windows installer.

## Getting Started

1. Download or clone this repository.
2. Extract the files into a writable folder if downloading a ZIP.
3. Open the application folder and run **Run_App.bat**.
4. Complete any required installation prompts.
5. Click **Setup / Login** and configure an AWS profile using access keys or SSO.
6. Click **Refresh profiles**, select your profile, and choose **Verify account**.
7. Enter your S3 bucket name and region.
8. Click **Go** or **Refresh files**, then begin managing your files.

Press **F1** to open the setup guide. The same instructions are available in **AWS Setup Readme.txt**.

## AWS Permissions

The application uses the permissions of the selected AWS profile.

| Operation | Permission |
|---|---|
| Browse bucket contents | `s3:ListBucket` |
| Read bucket location | `s3:GetBucketLocation` |
| Download files and load thumbnails | `s3:GetObject` |
| Upload or replace files | `s3:PutObject` |
| Delete files | `s3:DeleteObject` |
| Preserve tags while editing | `s3:GetObjectTagging`, `s3:PutObjectTagging` |
| List all bucket names | `s3:ListAllMyBuckets` |

Customize **S3_FileManager_Policy_Template.json** with your bucket name before applying it.

You can enter a bucket name directly without permission to list all buckets. Encrypted objects may require additional AWS KMS permissions. Bucket policies and organization restrictions also apply.

## File Views and Image Previews

Choose a layout from the **View** menu or view dropdown. Your chosen layout is saved with your project.

Supported image formats include PNG, JPEG, GIF, WebP, BMP, TIFF, and ICO. GIF and TIFF previews use the first frame.

Click an image to open the preview window. Use Ctrl/Shift-click or checkboxes to select images without opening a preview.

Preview limits:

- Maximum file size: **32 MB**
- Maximum image size: **40 megapixels**
- HEIC, RAW, SVG, and animated playback are not supported

Thumbnails load in the background for visible items and require permission to download the objects.

## Editing Files

Select a UTF-8 text file and choose **Edit file**. The editor supports files up to **5 MB**.

**Save to S3** checks the original object’s ETag before replacing it. If the remote file changed, reopen it and reconcile your edits before saving again.

HTML files are edited as text; they are not rendered or executed.

The editor preserves common metadata and supported encryption settings. Tag preservation is optional and requires tagging permissions. Advanced properties such as ACLs and Object Lock settings are not fully preserved.

## Projects and Credentials

Project files use the **.awsproj** extension and store application settings and AWS profile references.

Optional encrypted login backups:

- Include profiles from the local AWS configuration and credentials files.
- Use Windows DPAPI protection.
- Normally require the original Windows user and computer to restore.
- Do not include cached SSO or browser login sessions.

No AWS credentials or personal account settings are bundled with the application. AWS CLI manages local authentication storage.

**Do not commit credentials, private project files, or exported account information to GitHub.**

## Build an EXE or Installer

| Script | Purpose |
|---|---|
| **Run_App.bat** | Check prerequisites and launch the application |
| **Build_EXE.bat** | Build `dist/AWSAccountManager.exe` using PyInstaller |
| **Create_Installer.bat** | Build a Windows installer using Inno Setup |

Build scripts check for required tools and install or offer installation of missing dependencies. Run Windows builds on Windows.

## Important Notes

- Uploads and downloads may overwrite matching files.
- Deletion requires confirmation.
- Stopping an operation does not undo completed changes.
- Downloads using sync do not delete extra local files.
- Thumbnail loading, requests, storage, and transfers may incur AWS charges.
- The application cannot bypass AWS permissions.
- Windows GUI behavior, live AWS operations, and installer builds should be validated in your environment.

## Author

**Bob Paydar**
