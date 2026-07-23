# Publishing AutoDQ ADQL to the Visual Studio Code Marketplace

The Python distribution bundles the ADQL extension for offline installation,
but that does not create a Visual Studio Marketplace listing. Marketplace
publication produces the searchable extension ID `autodq.adql` and enables
normal Visual Studio Code installation and automatic updates.

## 1. Create or confirm the publisher

Sign in to the
[Visual Studio Marketplace publisher portal](https://marketplace.visualstudio.com/manage/publishers/)
with a Microsoft account and create a publisher with:

- Publisher ID: `autodq`
- Display name: `AutoDQ`

The publisher ID is permanent and must exactly match the `publisher` value in
`src/autodq/vscode/extension/package.json`. If `autodq` is unavailable, choose
a unique publisher ID and update the manifest and release tests before
packaging.

## 2. Package and test locally

Node.js 20 or newer is required. From the repository root:

```bash
cd src/autodq/vscode/extension
npm test
npx --yes @vscode/vsce@3.9.2 package --out ../../../../../dist/autodq-adql-0.2.2.vsix
```

Install the VSIX before public publication:

```bash
code --install-extension ../../../../../dist/autodq-adql-0.2.2.vsix --force
```

Reload Visual Studio Code, open a representative `.adql` file, and verify
syntax highlighting, notebook selection, cell execution, rich output, and the
Windows/macOS/Linux AutoDQ command resolution relevant to the test machine.

## 3. First publication

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

## 4. Automated publication from GitHub Actions

The repository includes `.github/workflows/publish-vscode.yml`. It validates
the requested version, packages the exact VSIX, uploads it as a workflow
artifact, and optionally publishes it behind the protected
`vscode-marketplace` GitHub environment.

For PAT-based publication:

1. Create an Azure DevOps Personal Access Token for **All accessible
   organizations** with **Marketplace → Manage** as its only required scope.
2. Add it to the GitHub repository as an Actions secret named `VSCE_PAT`.
3. Create a GitHub environment named `vscode-marketplace` and require a manual
   reviewer.
4. Run **Publish VS Code Extension**, enter `0.2.2`, and select whether to
   publish or only produce the VSIX artifact.

Never place the token in `package.json`, a command line committed to the
repository, or a local `.env` file.

## 5. Future versions

Visual Studio Marketplace versions are immutable. Before every update:

1. Increment the three-part extension version in `package.json` and
   `src/autodq/vscode/__init__.py`.
2. Update the extension changelog and user documentation.
3. Run the extension tests and package validation.
4. Test the VSIX locally.
5. Run the guarded publication workflow with the exact new version.

Microsoft is retiring global Azure DevOps PATs on December 1, 2026. Migrate
automated publication to Microsoft Entra ID workload identity before that date;
the manual VSIX packaging and Marketplace upload path remains available for
release recovery.
