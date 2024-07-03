# Verifying and Installing PDM

This document provides a script to safely download, verify, and install PDM.

This script does the following:
1. Downloads the PDM installer and its official checksum.
2. Calculates the SHA256 checksum of the downloaded installer.
3. Compares the calculated checksum with the official one.
4. If the checksums match, it proceeds with the installation.
5. If the checksums don't match, it aborts the installation and cleans up the downloaded files.

## Verification and Installation Script

Save the following script to a file named `install_pdm.sh`:

```bash
#!/bin/bash

set -e

# URLs for the PDM installer and its checksum
INSTALLER_URL="https://pdm-project.org/install-pdm.py"
CHECKSUM_URL="https://pdm-project.org/install-pdm.py.sha256"

# Download the PDM installer
echo "Downloading PDM installer..."
curl -sSL -o install-pdm.py "$INSTALLER_URL"

# Download the official checksum
echo "Downloading official checksum..."
curl -sSL -o official_checksum.sha256 "$CHECKSUM_URL"

# Calculate the checksum of the downloaded installer
calculated_checksum=$(sha256sum install-pdm.py | cut -d ' ' -f 1)

# Read the official checksum
official_checksum=$(cat official_checksum.sha256 | cut -d ' ' -f 1)

# Compare checksums
if [ "$calculated_checksum" = "$official_checksum" ]; then
    echo "Checksum verification successful."
    echo "Installing PDM..."
    python3 install-pdm.py
    echo "PDM installed successfully."
else
    echo "Checksum verification failed. Aborting installation."
    exit 1
fi

# Clean up temporary files
rm install-pdm.py official_checksum.sha256

echo "Installation complete. You can now use PDM."
```

## Usage Instructions

1. Save the script above to a file named `install_pdm.sh`.
2. Make the script executable:
   ```bash
   chmod +x install_pdm.sh
   ```
3. Run the script:
   ```bash
   ./install_pdm.sh
   ```

This script will download the PDM installer, verify its integrity using the official SHA256 checksum, and install PDM if the verification is successful.

## Security Note

Always exercise caution when downloading and running scripts from the internet. This script is provided to enhance security by verifying the PDM installer before running it, but you should always review scripts before executing them.