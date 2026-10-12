# Unity, after the page

The roller in this folder is the thing to publish. Unity is a later tool, not a second copy of the dice page.

Unity Hub is not installed here. `sudo` needs a password, so the install was not started. There is no Unity ID on this machine, and none should be created unless you want one. Stop if Hub asks you to sign in or to accept a Personal license, and decide that yourself.

When you want Hub:

```bash
wget -qO- https://hub.unity3d.com/linux/keys/public | gpg --dearmor | sudo tee /etc/apt/keyrings/unityhub.gpg > /dev/null
sudo chmod 644 /etc/apt/keyrings/unityhub.gpg
echo "deb [signed-by=/etc/apt/keyrings/unityhub.gpg] https://hub.unity3d.com/linux/repos/deb stable main" | sudo tee /etc/apt/sources.list.d/unityhub.list
sudo apt update
sudo apt install unityhub
unityhub
```

Then install the current LTS editor and the WebGL module from inside Hub. The Linux editor is not built for arm64. After it is installed, note the editor version and the path Hub reports, and write them under this file so the project can be reopened with the same editor.

A Unity icosphere is a subdivided ball, not a d20. A twenty-sided die is the 20-face solid already built for the page (`assets/die.json`). Do not rebuild this roller in Unity unless you ask for that.
