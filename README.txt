WHAT IS NEW IN 1.4
Seven layouts: Extra large icons, Large icons (default), Medium icons, Small icons,
List, Details and Tiles. All views support checkboxes and existing file actions.
Image thumbnails load for visible items in background, with a 96 MB cache limit.
Supported: PNG/JPEG/GIF/WebP/BMP/TIFF/ICO (first frame). Up to 32 MB / 40 megapixels.
Single-click image preview: Fit, 100%, zoom, pan, rotation, PNG copy and Close.
Ctrl/Shift-click selects without preview. Image fetching needs GetObject permission
and can incur AWS request/transfer costs. No images or account data are bundled.
Pillow is checked/installed by launch/build scripts and included in the EXE.
The selected file view is saved in projects. Color contrast and alternating rows
improve file visibility. Existing features and generic AWS setup are retained.

WHAT IS NEW IN 1.3
Generic distribution: no personal bucket, IAM username, account ID or credentials.
Region starts blank and uses the selected AWS profile/environment default unless
the user enters a region. Setup examples use generic placeholders.
S3_FileManager_Policy_Template.json must be customized with your bucket name.
Bob Paydar branding is retained. Existing .awsproj files remain compatible.
User-saved projects may contain personal settings; they are not included here.

WHAT IS NEW IN 1.2
Help menu / F1 opens a searchable, resizable offline guide with topic navigation,
adjustable text size, clickable references and local current-setup information.
AWS Setup Readme.txt contains the same guide. Built-in help is bundled in the EXE.
Existing features and project formats are retained.

WHAT IS NEW IN 1.1
- Fixed file refresh: old Refresh refreshed only AWS profiles, not S3 contents.
  Refresh profiles now has an explicit label. Refresh files / F5 reloads S3.
- Successful uploads, edits and deletes automatically refresh the current folder.
  Batch partial failures also refresh so completed changes are visible.
- Upload multiple files at once. File operations capture profile/region at start.
- Folder navigation, Back / Up / Root, editable address, double-click to open.
- Checkbox selection, Ctrl/Shift row selection, Space to toggle highlighted rows,
  Select all / none / invert, context menu, sortable columns and local filtering.
- Checked items take precedence over highlighted rows, including checked items
  hidden by a filter. The count shows all checked items. Select none clears them.
- Select all/invert act on currently visible loaded rows. Load more fetches the
  next 1,000 entries. No selection action silently selects unloaded objects.
- Batch download and delete support files. Open folders to select contents;
  Download folder retains the original recursive sync functionality.
- New folder and Copy S3 path actions.
- Built-in UTF-8 text editor (up to 5 MB), including HTML, JSON, CSS and Python.
  HTML is edited as text and is never rendered/executed by the app.
  Save to S3 uses an ETag conditional write: conflicting remote changes cause
  an error; reopen/reconcile instead of silently overwriting someone else's edit.
  It preserves UTF-8 BOM, normal CRLF/LF convention, common HTTP headers, custom
  metadata and SSE-KMS settings. It does not preserve ACLs, Object Lock settings,
  expiry, or all advanced object properties. Versioned buckets create a new version.
  Tags are NOT retained unless Preserve tags is checked. That option requires
  s3:GetObjectTagging and s3:PutObjectTagging permissions.
- Project menu: New/Open/Save/Save As, Ctrl+O/Ctrl+S, .awsproj files.
  Projects save profile, region, bucket, folder, download path, filter, recursive
  view, output format and window geometry. AWS profile references work immediately
  when those profiles already exist on the computer.
- Optional Include encrypted AWS login backup saves ALL configured profiles from
  AWS config/credentials files, encrypted with Windows DPAPI (current user scope).
  Enable it in Project before saving. Default is OFF. No plaintext secrets are
  included in projects. Restoring is explicitly confirmed and replaces matching
  profile sections while preserving unrelated profiles. Only open trusted projects.
  DPAPI normally needs the original Windows login and computer. SSO/login cached
  tokens are not copied, and expired temporary sessions must be signed in again.
  AWS CLI's own credentials file uses its normal plaintext storage after restore.

VALIDATION FOR 1.1
13 unit tests passed; the Windows-only DPAPI round-trip test was skipped on Linux.
Tests cover command parsing, profile isolation, secret redaction, project validation,
profile merge, safe download paths, pagination arguments, batch account capture,
and completion ordering (callbacks run after the app leaves its busy state).
Windows GUI, real AWS calls, DPAPI and Windows packaging require Windows validation.
Run: python -m unittest -v

AWS ACCOUNT MANAGER 1.4.0
Programmer: Bob Paydar

QUICK START
1. Extract this entire ZIP into a writable local folder.
2. Double-click Run_App.bat.
3. If Python is missing, the launcher offers installation through winget.
   Otherwise install Python 3.10+ from python.org with pip and Tcl/Tk enabled.
4. If AWS CLI is missing, accept the app's official AWS CLI installer prompt.
   Windows may request administrator approval. Finish setup and click Refresh.
5. Use Setup / Login to configure a named profile, SSO, or console-based login.
   Complete the separate console prompts. Click Refresh, select your profile,
   set the region, then Verify account.
6. Enter a bucket name directly if your account cannot list all buckets.
   Browse objects, choose a local folder, Preview download, then Download.

FILES
Run_App.bat          Checks Python/Tk, prepares .venv, launches the app.
Build_EXE.bat        Checks prerequisites, installs missing PyInstaller in .venv,
                    creates dist\AWSAccountManager.exe on Windows.
Create_Installer.bat Builds EXE, checks/offers Inno Setup installation, compiles
                    installer_output\AWSAccountManager_Setup_1.4.0.exe.
bootstrap.py        Environment and build helper.
aws_manager.py      Application source; Pillow for image previews.
installer.iss       Inno Setup installer definition with uninstall support.
requirements.txt    Runtime requirements explanation.
requirements-build.txt  PyInstaller build dependency.
AWS_CLI_Help.txt     User-provided AWS CLI reference.
test_manager.py     Unit tests using no AWS credentials or network.

ACCOUNT ACCESS
The application manages profiles you are authorized to use. Roles and SSO
configured in AWS CLI are supported. It does not automatically gain access to
other accounts, create IAM permissions, or bypass organization restrictions.
AWS CLI is a separate executable; AWS Tools for PowerShell is not required.
Use Setup / Login to configure credentials locally. No credentials are included
in this package. Replace any access keys previously exposed in chat.
The app removes credential environment overrides for its AWS subprocesses so
that the chosen profile controls authentication. AWS CLI retains credentials
in its normal local storage (which can include plaintext credentials files).

FEATURES AND BEHAVIOR
- Multiple profiles, editable region, STS account/ARN verification.
- Bucket list and paginated object browser (1,000 keys per page).
- Sync download with dry-run preview, single-file download, upload and deletion.
- Sync never adds --delete. Local files can be overwritten by downloads.
- Uploads/deletes require confirmation. Versioned deletes may add a delete marker.
- AWS console accepts all service commands supported by the installed CLI.
  Arguments use quotes for grouping; Windows backslashes are preserved.
  It is not a PowerShell shell: no pipes, redirection, or shell expansion.
  Quote JSON with single quotes. Use file:// arguments for complex payloads.
- Background execution, responsive controls, activity output, Stop and export.
- Stop cannot undo completed uploads, downloads or AWS resource changes.
- Keys and common JSON credential fields are redacted in displayed output.
  Arbitrary service output can still contain sensitive data. No automatic logs
  are saved; review output before exporting or sharing it.
- Output display retains approximately 12,000 lines. CLI console streams results;
  structured browser responses are capped at 16 MB. Load more appends another page to the table.
- Explorer folders use S3 common prefixes. Toggle All subfolders for a flat view.
- Glacier objects may require restore; SSE-KMS downloads need kms:Decrypt.
- File downloads must use keys compatible with Windows filenames. Use a suitably
  isolated destination and review the dry run for unusual object key names.

TROUBLESHOOTING
AccessDenied for ListObjectsV2: profile needs s3:ListBucket on the bucket ARN.
Downloads also need s3:GetObject on arn:aws:s3:::BUCKET/*; uploads and deletions
need corresponding permissions. Use bucket-scoped policies where practical.
SSO expired: Setup / Login > SSO login.
CLI not detected after installation: restart app/terminal, then Refresh.
Python/Tk missing: modify Python installation; tkinter is not a pip package.
Build fails: read console error. Internet is required for missing dependencies.
Inno Setup missing: accept winget installation or install from jrsoftware.org.
The EXE and installer are unsigned and may trigger Windows SmartScreen.
Uninstall removes the app, not your AWS CLI, credentials, or downloaded data.

VALIDATION
Python syntax and unit tests were checked in the development environment.
Windows UI, real AWS operations, UAC installer, EXE and Inno Setup builds must
be validated on your Windows computer. No compiled Windows EXE is included.

REFERENCES
https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
https://docs.aws.amazon.com/cli/latest/reference/s3/sync.html
https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html
https://jrsoftware.org/ishelp/topic_compilercmdline.htm
