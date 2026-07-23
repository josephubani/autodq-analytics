# Distributing the AutoDQ ADQL VS Code Extension

The Python distribution bundles the ADQL extension for offline installation,
but `pip install autodq` does not register it as a VS Code extension. The
recommended account-independent distribution is a downloadable VSIX attached
to a GitHub Release. Marketplace publication remains optional.

## 1. Package and test locally

Node.js 20 or newer is required. From the repository root:

```bash
cd src/autodq/vscode/extension
npm test
npx --yes @vscode/vsce@3.9.2 package --out ../../../../../dist/autodq-adql-0.2.2.vsix
```

Install the VSIX before publishing the GitHub Release:

```bash
code --install-extension ../../../../../dist/autodq-adql-0.2.2.vsix --force
```

Reload VS Code, open a representative `.adql` file, and verify syntax
highlighting, notebook selection, cell execution, rich output, and AutoDQ
command resolution on the test machine.

## 2. Publish the downloadable VSIX on GitHub

The repository's **Publish VS Code Extension** workflow can create a permanent
GitHub Release without a Microsoft account or additional secret:

1. Push the extension source and workflow to the `main` branch.
2. Open the repository's **Actions** tab.
3. Select **Publish VS Code Extension** and choose **Run workflow**.
4. Enter the exact extension version from `package.json`.
5. Leave **Attach the VSIX to an adql-vVERSION GitHub Release** enabled.
6. Leave **Publish to Visual Studio Marketplace** disabled.
7. Run the workflow.

For version `0.2.2`, the workflow creates the tag and release
`adql-v0.2.2`, then attaches:

- `autodq-adql-0.2.2.vsix`
- `autodq-adql-0.2.2.vsix.sha256`

The permanent download page is:

```text
https://github.com/josephubani/autodq-analytics/releases/tag/adql-v0.2.2
```

The direct VSIX download is:

```text
https://github.com/josephubani/autodq-analytics/releases/download/adql-v0.2.2/autodq-adql-0.2.2.vsix
```

Windows users can download the VSIX and choose **Extensions → … → Install
from VSIX**, or run:

```powershell
code --install-extension .\autodq-adql-0.2.2.vsix --force
python -m pip install --upgrade autodq
```

The checksum can be verified in PowerShell with:

```powershell
Get-FileHash .\autodq-adql-0.2.2.vsix -Algorithm SHA256
```

Compare that value with the downloaded `.sha256` file. Manually installed
VSIX extensions do not receive Marketplace automatic updates, so users must
download and install each new version.

### Manual GitHub fallback

If GitHub Actions is unavailable, open **Releases → Draft a new release** in
the repository, create the `adql-vVERSION` tag, and drag the tested VSIX into
the binary attachments area before publishing the release.

## 3. Optional: create or confirm the Marketplace publisher

Sign in to the
[Visual Studio Marketplace publisher portal](https://marketplace.visualstudio.com/manage/publishers/)
with a Microsoft account and create a publisher with:

- Publisher ID: `autodq`
- Display name: `AutoDQ`

The publisher ID is permanent and must exactly match the `publisher` value in
`src/autodq/vscode/extension/package.json`. If `autodq` is unavailable, choose
a unique publisher ID and update the manifest and release tests before
packaging.

## 4. Optional Marketplace publication

The simplest first publication is a manual VSIX upload:

1. Open the publisher portal and select the `autodq` publisher.
2. Choose **New extension** and then **Visual Studio Code**.
3. Upload `dist/autodq-adql-0.2.2.vsix`.
4. Complete Marketplace validation and make the extension public.

After publication, the listing is expected at:

```text
https://marketplace.visualstudio.com/items?itemName=autodq.adql
```

Users can then install it with:

```bash
code --install-extension autodq.adql
```

### Automated Marketplace publication

The same workflow validates the requested version, packages the exact VSIX,
creates the GitHub download, and can optionally publish it behind the protected
`vscode-marketplace` GitHub environment.

For PAT-based publication:

1. Create an Azure DevOps Personal Access Token for **All accessible
   organizations** with **Marketplace → Manage** as its only required scope.
2. Add it to the GitHub repository as an Actions secret named `VSCE_PAT`.
3. Create a GitHub environment named `vscode-marketplace` and require a manual
   reviewer.
4. Run **Publish VS Code Extension**, enter `0.2.2`, and select whether to
   publish to the Marketplace in addition to the GitHub Release.

Never place the token in `package.json`, a command line committed to the
repository, or a local `.env` file.

## 5. Future versions

Visual Studio Marketplace versions are immutable. Before every update:

1. Increment the three-part extension version in `package.json` and
   `src/autodq/vscode/__init__.py`.
2. Update the extension changelog and user documentation.
3. Run the extension tests and package validation.
4. Test the VSIX locally.
5. Run the workflow with GitHub Release creation enabled.
6. Tell users to download and install the new VSIX with `--force`.

Microsoft is retiring global Azure DevOps PATs on December 1, 2026. Migrate
automated publication to Microsoft Entra ID workload identity before that date;
the manual VSIX packaging and Marketplace upload path remains available for
release recovery.
