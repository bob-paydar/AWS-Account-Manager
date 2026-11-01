"""Single source for the built-in guide and AWS Setup Readme.txt."""
import json

POLICY = {
 'Version':'2012-10-17',
 'Statement':[
  {'Effect':'Allow','Action':['s3:ListBucket','s3:GetBucketLocation'],'Resource':'arn:aws:s3:::YOUR-BUCKET-NAME'},
  {'Effect':'Allow','Action':['s3:GetObject','s3:PutObject','s3:DeleteObject','s3:AbortMultipartUpload','s3:GetObjectTagging','s3:PutObjectTagging'],'Resource':'arn:aws:s3:::YOUR-BUCKET-NAME/*'}
 ]
}
TOPICS = [
('Start here', '''AWS ACCOUNT MANAGER — SETUP AND USER GUIDE
Programmer: Bob Paydar

Follow steps 1–6 to connect your AWS account, then read the file management topics.
You need permission to use the account and bucket. This program uses AWS CLI;
it cannot grant itself access or bypass IAM rules.

Choose a sign-in method:
• Organization / company account: use IAM Identity Center (SSO) if provided.
• Personal account using IAM access keys: follow the IAM user instructions.
Do not create access keys for the AWS root user.

The application and this text guide contain the same setup topics. In the Help
window, search topics, click a section, use Previous / Next, adjust text size,
copy a topic, or save the complete guide. F1 opens Help from the main window.
The Current setup panel shows local settings only; Verify account checks AWS.

Examples use YOUR-BUCKET-NAME and YOUR-REGION placeholders. Replace these with
your own bucket and its actual region. No account or region is preset. A profile name is a local label; it does not
have to match your IAM username.'''),
('1. Install Python and AWS CLI', '''STEP 1 — PREPARE YOUR WINDOWS COMPUTER

1. Extract the whole ZIP into a writable folder. Do not run inside the ZIP.
2. Double-click Run_App.bat. It checks Python 3.10+ and prepares a local .venv.
3. If Python is absent, accept the launcher’s winget installation offer, or
   install Python from https://www.python.org/downloads/windows/.
   Include pip and Tcl/Tk. Reopen the BAT after installation to refresh PATH.
4. The Python app uses tkinter and Pillow. The launcher installs Pillow if needed.
   Missing tkinter must be repaired using the Python installer, not pip.
5. If AWS CLI is absent, the app offers the official AWS CLI v2 MSI installer.
   Complete Windows Installer/UAC prompts, then restart the app if necessary.

Manual AWS installation:
https://awscli.amazonaws.com/AWSCLIV2.msi

In PowerShell, check installation:
aws --version

You should see aws-cli/2... . AWS Tools for PowerShell is a different product
and is not required. Recent CLI v2 is recommended for conditional file saves.
Installation and dependency downloads need internet access.'''),
('2. Find your bucket and region', '''STEP 2 — IDENTIFY THE STORAGE LOCATION

1. Sign in to https://console.aws.amazon.com/s3/.
2. Open your bucket. Copy its exact name and note its AWS Region.
3. Use the name in the app’s Bucket field, for example: YOUR-BUCKET-NAME.
4. Enter the actual bucket region code, or leave Region blank to use the AWS
   profile/environment default. Region codes below are general examples.

Useful examples:
US East (Ohio)       us-east-2
US East (N. Virginia) us-east-1
US West (Oregon)     us-west-2
Europe (Ireland)    eu-west-1

A bucket ARN such as arn:aws:s3:::YOUR-BUCKET-NAME identifies the bucket but does not
contain its region. The app also accepts a standard bucket ARN or s3:// name.
For a folder, use Folder / prefix, for example documents/.
Leave Folder / prefix empty to browse the bucket root.'''),
('3A. Sign in with SSO', '''STEP 3A — ORGANIZATION / IAM IDENTITY CENTER SIGN-IN

Use this route when your organization provides AWS IAM Identity Center access.
Your AWS administrator must assign you an account and role with S3 permissions.

1. Ask your administrator for the SSO start URL (or issuer URL), SSO region,
   account and role. The SSO region can differ from your S3 bucket region.
2. In the app click Setup / Login.
3. Enter a profile name, for example company-s3.
4. Click Configure SSO and complete the separate console prompts.
5. Enter the SSO session name, URL and SSO region. For registration scopes,
   use the offered default unless your administrator specifies otherwise.
6. Complete browser authentication, select the account and role, and enter
   the default client region and json output format.
7. Return to the app, click Refresh profiles, select company-s3 and Verify account.

When your session expires, use Setup / Login > SSO login for the same profile.
You do not need an IAM access key for this route. Skip step 3B.

Equivalent PowerShell commands:
aws configure sso --profile company-s3
aws sso login --profile company-s3

Console-based login is also available in Setup / Login on recent AWS CLI versions.
Follow its browser prompts if your AWS account setup supports that route.'''),
('3B. Create an IAM user and access key', '''STEP 3B — IAM ACCESS-KEY SIGN-IN

Use this route if you are using IAM user keys instead of SSO.

1. Open https://console.aws.amazon.com/iam/ with an identity allowed to manage IAM.
2. Under Access Management choose IAM users (or Users).
3. Select an existing suitable user, or Create user; example: s3-file-manager.
4. CLI-only use does not require AWS Management Console password access.
5. Complete user creation. Do not attach AdministratorAccess just for S3 files.
6. Grant bucket permissions using step 4 below.
7. Open the user > Security credentials > Access keys > Create access key.
8. Choose Command Line Interface (CLI), follow the prompts, and create the key.
9. Save both the Access key ID and Secret access key securely, or download the CSV.

AWS shows the secret only when the key is created. If lost, create a replacement;
the access key ID alone cannot reveal the secret. If a key was exposed in a chat,
screenshot or public file, deactivate/delete it and configure a new key pair.
Do not paste credentials into the app’s command console or share them with others.
Enter them only into the AWS configuration prompts on your own computer.'''),
('4. Grant S3 permissions', '''STEP 4 — ALLOW THE REQUIRED BUCKET OPERATIONS

For an IAM user:
1. Open IAM > Users > your user > Permissions.
2. Choose Add permissions > Create inline policy (wording can vary).
3. Select JSON and paste the policy below.
4. Replace BOTH occurrences of YOUR-BUCKET-NAME with your bucket name.
5. Choose Next, give it a name such as S3-FileManager, and Create policy.
   An inline policy is attached directly to that user.

If you create a standalone managed policy under IAM > Policies instead, also
attach it to the user/group/role afterward. For SSO, ask your administrator to
add equivalent permissions to your assigned permission set and provision it.

This policy allows browse/read/upload/replace/delete in one bucket. Tag actions
support Preserve tags in the editor. Remove DeleteObject if deletion is unwanted.
For download-only use, retain ListBucket/GetBucketLocation/GetObject only.

'''+json.dumps(POLICY,indent=2)+'''

LIST BUCKETS BUTTON
The policy above does not allow listing all bucket names. You can type a bucket
name directly and browse it. To enable List buckets, an administrator can grant
s3:ListAllMyBuckets on Resource "*" as a separate statement. This reveals bucket
names; it does not grant file access to those other buckets.

Important distinctions:
• Bucket actions use arn:aws:s3:::YOUR-BUCKET-NAME.
• Object actions use arn:aws:s3:::YOUR-BUCKET-NAME/*.
• AmazonS3ReadOnlyAccess permits reads but not uploads or edits.
• Other attached policies continue to apply; adding a narrow policy does not
  remove broader permissions already granted elsewhere.
• Bucket policies, organization restrictions and explicit denies may still block
  access. SSE-KMS objects may need KMS key permissions such as kms:Decrypt and
  kms:GenerateDataKey plus a compatible key policy.

Permission updates do not require a new access key. Allow a short propagation
interval and retry. The example targets standard commercial AWS S3 buckets.'''),
('5. Configure the application profile', '''STEP 5 — CONNECT THE APP USING AN IAM KEY

Skip key entry if you completed the SSO route.

1. Click Setup / Login.
2. Enter a local profile name, for example my-s3-profile.
3. Click Configure access keys. A separate console opens.
4. At AWS Access Key ID, enter your key ID.
5. At AWS Secret Access Key, enter the matching secret from the same key pair.
6. At Default region name, enter your bucket’s actual AWS region code.
7. At Default output format, enter json.
8. If asked to configure AWS skills/MCP for an AI coding agent, choose n;
   this optional integration is not required by this application.
9. Return to the app > Refresh profiles > choose my-s3-profile.

Equivalent PowerShell command:
aws configure --profile my-s3-profile

A [None] prompt means a setting has not been saved yet. The secret key is not
your AWS website password. AWS CLI saves profiles locally, usually under
%USERPROFILE%\\.aws\\config and %USERPROFILE%\\.aws\\credentials.
The credentials file may contain plaintext keys. Use SSO when appropriate.

The app deliberately removes environment credential overrides from its CLI
subprocesses so the profile selected in the app controls the AWS account.'''),
('6. Verify and make a first transfer', '''STEP 6 — VERIFY THE ACCOUNT AND TEST ACCESS

1. Select your profile and region in the main window.
2. Click Verify account. Confirm the returned account number and ARN are yours.
   Verification confirms the identity, not every S3 permission.
3. Type your bucket name. Clear Folder / prefix and Filter loaded items.
4. Click Go or Refresh files (F5). If List buckets is denied, entering the bucket
   directly can still work with a bucket-scoped policy.
5. Choose a local download folder. Use Preview sync to see proposed downloads.
6. Download selected files or use Download folder for all files under the prefix.
7. To test upload, choose a small harmless file with a new name, such as 0.html.
8. Click Upload files, select it and confirm the destination. Upload completion
   automatically reloads the current folder. Matching keys may be overwritten.

PowerShell identity test:
aws sts get-caller-identity --profile my-s3-profile

PowerShell download example:
aws s3 sync s3://YOUR-BUCKET-NAME "C:\\S3-Backup" --profile my-s3-profile --region YOUR-REGION

AWS requests, storage and transfers may incur account charges. Preview sync
lists proposed changes but still makes read/list requests.'''),
('7. Explorer and selection', '''BROWSE AND MANAGE FILES

• Choose Extra large icons, Large icons (default), Medium icons, Small icons, List,
  Details or Tiles using the View menu or dropdown. The selected view is saved
  in projects. Double-click a folder to open it. Back, Up and Root navigate folders.
• Enter a path in Folder / prefix and press Enter or Go.
• All subfolders switches to a flat recursive listing.
• Refresh profiles reloads account profile names. Refresh files / F5 reloads S3.
• Load more appends the next page (up to 1,000 entries per request).
• Filter loaded items searches only entries already loaded; it is not a full
  bucket search. Clear the filter when a file seems missing.
• Click a column heading to sort the loaded entries.

IMAGE THUMBNAILS AND PREVIEW
PNG, JPEG, GIF, WebP, BMP, TIFF and ICO files show thumbnails in every view.
Thumbnails download automatically for visible files and require s3:GetObject.
These requests and transfers may incur AWS charges. Files over 32 MB or
40 megapixels keep a file icon; download them for local viewing. HEIC, RAW,
SVG and animated playback are not supported. GIF/TIFF use the first frame.
Click an image to open a larger preview. Use Fit, 100%, +/-, mouse-wheel zoom,
drag to pan, rotate left/right, Save PNG copy, and Close (or Esc). Preview
rotation does not change the S3 file. Ctrl/Shift-click selects without preview.
Checkbox clicks only change selection. Failed thumbnails keep a file icon;
click the image to see the error. Refresh files retries failed thumbnails.

SELECTION RULES
Click a checkbox to check a file. Ctrl/Shift can select multiple highlighted rows.
Space toggles checks for highlighted rows. Checked rows take precedence over
highlighted rows, including checked rows hidden by a filter. Check the count.
Select none clears both checks and highlights. Select all and Invert act on
visible loaded entries, not unloaded pages. Load more before selecting more.

Upload files supports multiple local files. Download selected and Delete selected
operate on files; open folders first to manage their contents. Download folder
recursively syncs the prefix. Sync does not delete extra local or remote files,
but may overwrite local files. Stop cannot roll back completed transfers.
Right-click offers common actions. Copy S3 path copies selected object locations.'''),
('8. Edit a file', '''EDIT TEXT WITHOUT LEAVING THE APP

1. Select exactly one UTF-8 text file and click Edit file (or double-click it).
2. Edit the text. The built-in editor supports files up to 5 MB.
3. Save local copy exports a local copy. Save to S3 replaces the remote object.
4. Confirm the destination and profile before saving.

HTML is treated as source text and is not rendered or executed. Binary files
and non-UTF-8 text should be downloaded for editing in another application.
Save to S3 uses the downloaded ETag to avoid overwriting a file changed remotely.
If a conflict occurs, reopen the file and reconcile your changes. Keep a local
copy of unsaved edits first. Use a recent AWS CLI v2 for --if-match support.

The editor preserves common HTTP headers, custom metadata and supported encryption
settings. Preserve tags is optional and requires GetObjectTagging/PutObjectTagging.
Without it, tags are not retained. Advanced properties such as ACLs, Object Lock
settings and expiry are not fully preserved. Versioned buckets create a new version.'''),
('9. Projects and saved login information', '''SAVE AND REOPEN YOUR WORKSPACE

Project > Save project / Save project as creates an .awsproj file.
Project > Open project restores profile name, region, bucket, folder, download
path, filtering, recursive view, output format and window geometry.
Keyboard shortcuts: Ctrl+S save project; Ctrl+O open project.

Profiles already remain saved in AWS CLI storage. Normal project files reference
them without copying secrets. They do not contain the actual S3 files.

OPTIONAL ENCRYPTED LOGIN BACKUP
1. In Project, check Include encrypted AWS login backup (this Windows user).
2. Save the project. It includes an encrypted snapshot of ALL configured profiles
   in AWS config/credentials files, not only the active profile.
3. When opening it, choose whether to restore the login backup.
4. Matching profile sections are replaced; unrelated profiles are preserved.

Windows DPAPI protects the backup for the originating Windows user, normally
on the same computer. It is not a portable credential export for another PC.
SSO/browser session caches are not included. Expired sessions require sign-in.
After restoration, AWS CLI uses its normal local credential storage. Only open
projects from sources you trust; AWS profiles can contain credential processes.'''),
('10. Troubleshooting', '''COMMON PROBLEMS AND NEXT STEPS

FILE UPLOADED BUT NOT VISIBLE
Confirm account/profile, bucket and folder. Clear Filter loaded items, press F5,
and use Load more if necessary. 0.html uploaded at root will not appear while
viewing a different folder. Uploads now refresh automatically; the old profile
refresh button did not refresh S3 files.

AccessDenied / ListObjectsV2 / s3:ListBucket
Grant ListBucket on the bucket ARN. Confirm the identity with Verify account.
ListAllMyBuckets is only needed for the List buckets button.

AccessDenied when uploading or editing
Grant PutObject on the bucket’s object ARN ending in /*. Preserve tags needs the
tagging permissions in step 4. Check bucket policies and KMS restrictions too.

InvalidAccessKeyId / SignatureDoesNotMatch
Check that both credentials belong to the same active key pair. Reconfigure the
selected profile locally. Check your Windows clock. Never share the secret.

ExpiredToken / SSO session expired
Use Setup / Login > SSO login or refresh your temporary credentials.

AWS CLI not found
Install AWS CLI v2 and reopen the app. Test aws --version in a new PowerShell.

Unknown option --if-match
Update AWS CLI v2, then retry. Do not remove the edit conflict protection.

PreconditionFailed / HTTP 412 during save
The object changed remotely. Save a local copy, reopen the remote file and merge.

Project login backup cannot decrypt
Use the original Windows account/computer, or reconnect with Setup / Login.
You can open project settings without restoring the encrypted backup.

Glacier / archived object download fails
The object may need a restore operation before downloading.

Python / Tcl/Tk / build errors
Run the BAT from an extracted writable folder. Repair Python with Tcl/Tk and pip.
Read the console output. Windows builds require Windows and internet for missing
build dependencies. UI and DPAPI behavior must be tested on your Windows PC.'''),
('11. Build EXE and installer', '''WINDOWS BUILD SCRIPTS

Run_App.bat checks Python, prepares .venv and starts the application.
Build_EXE.bat installs missing PyInstaller into .venv and creates:
dist\\AWSAccountManager.exe

Create_Installer.bat builds the EXE, checks/offers Inno Setup installation,
and creates a setup EXE under installer_output.
The installer includes AWS Setup Readme.txt for offline reference.

The built-in Help text is embedded in a Python module, so it remains available
in the standalone EXE even when no text guide file is alongside it.
The Windows installer has uninstall support. It does not bundle your AWS login
information or delete your AWS credentials/downloads on uninstall.
Unsigned executables may trigger Windows SmartScreen. These builds are local;
no compiled Windows EXE is included in the source ZIP.'''),
('Official references', '''OFFICIAL DOCUMENTATION

AWS CLI installation:
https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

IAM access keys:
https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html

IAM policies:
https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_create-console.html

SSO setup:
https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html

S3 identity policies:
https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-policies-s3.html

S3 conditional writes:
https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html

Microsoft Windows DPAPI:
https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata

Inno Setup compiler:
https://jrsoftware.org/ishelp/topic_compilercmdline.htm

Guide reviewed: November 1, 2026. AWS console wording may change.''')
]

def full_guide():
    return '\n\n'.join(title+'\n'+'='*len(title)+'\n\n'+body for title,body in TOPICS)+'\n'

def search_topics(query):
    terms=query.casefold().split()
    return [i for i,(title,body) in enumerate(TOPICS) if all(term in (title+' '+body).casefold() for term in terms)]
