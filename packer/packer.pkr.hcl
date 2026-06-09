packer {
  required_plugins {
    virtualbox = {
      version = ">= 1.0.0"
      source  = "github.com/hashicorp/virtualbox"
    }
  }
}

variable "iso_url" {
  type    = string
  default = "https://cdimage.debian.org/cdimage/weekly-builds/amd64/iso-cd/debian-testing-amd64-netinst.iso"
}

variable "iso_checksum" {
  type    = string
  default = "file:https://cdimage.debian.org/cdimage/weekly-builds/amd64/iso-cd/SHA256SUMS"
}

source "virtualbox-iso" "arda_os" {
  boot_command = [
    "<esc><wait>",
    "install <wait>",
    " preseed/url=http://{{ .HTTPIP }}:{{ .HTTPPort }}/preseed.cfg <wait>",
    "debian-installer/locale=en_US <wait>",
    "keyboard-configuration/xkb-keymap=us <wait>",
    "netcfg/get_hostname=arda-sovereign <wait>",
    "netcfg/get_domain=local <wait>",
    "fb=false <wait>",
    "debconf/frontend=noninteractive <wait>",
    "console-setup/ask_detect=false <wait>",
    "console-setup/layoutcode=us <wait>",
    "<enter><wait>"
  ]
  boot_wait            = "10s"
  cpus                 = 2
  memory               = 4096
  disk_size            = 20480
  guest_os_type        = "Debian_64"
  http_directory       = "packer/http"
  iso_checksum         = var.iso_checksum
  iso_url              = var.iso_url
  shutdown_command     = "echo 'arda' | sudo -S shutdown -P now"
  ssh_password         = "arda"
  ssh_username         = "arda"
  ssh_wait_timeout     = "10000s"
  vboxmanage = [
    ["modifyvm", "{{ .Name }}", "--vram", "128"],
    ["modifyvm", "{{ .Name }}", "--graphicscontroller", "vmsvga"]
  ]
  format               = "ova"
  output_directory     = "output-arda-os"
  vm_name              = "Arda-OS-Sovereign-v4.1"
}

build {
  sources = ["source.virtualbox-iso.arda_os"]

  provisioner "file" {
    source      = "./"
    destination = "/tmp/arda_os"
  }

  provisioner "shell" {
    scripts = ["packer/scripts/provision.sh"]
  }

  post-processor "manifest" {
    output     = "packer-manifest.json"
    strip_path = true
  }
}
