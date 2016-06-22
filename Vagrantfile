# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # All Vagrant configuration is done here. The most common configuration
  # options are documented and commented below. For a complete reference,
  # please see the online documentation at vagrantup.com.

  # Every Vagrant virtual environment requires a box to build off of.

  config.vm.box = 'centos-7.2-isf-ncharts.virtualbox.20160606'

  # config.vm.hostname = config.vm.box

  # The url from where the 'config.vm.box' box will be fetched if it
  # doesn't already exist on the user's system.
  config.vm.box_url = "/net/vagrant/raf/#{config.vm.box}.box"

  # Enable SSH agent forwarding to use host's SSH key w/ GitHub
  # Depend on addition of host's SSH key to host's SSH agent.
  # For more information, see https://coderwall.com/p/p3bj2a
  config.ssh.forward_agent = true

  config.vm.provider "virtualbox" do |v|
    # v.memory = 8192
    v.memory = 512
    v.cpus = 2
  end

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  # config.vm.network "forwarded_port", guest: 3000, host: 3000

  config.vm.network "forwarded_port", guest: 80, host: 8080
  config.vm.network "forwarded_port", guest: 8000, host: 8000


  use_nfs = (ENV['VAGRANT_USE_NFS'] and ENV['VAGRANT_USE_NFS'].downcase!='false' and ENV['VAGRANT_USE_NFS']!='0')
  folder_options = {}

  # uncomment private_network when using NFS to sync folder(s)
  if use_nfs
    config.vm.network "private_network", ip:"10.#{rand(255)}.#{rand(255)}.#{rand(2..255)}"
    folder_options[:type] = 'nfs'
  end

  config.vm.synced_folder ".", "/vagrant", folder_options
  config.vm.synced_folder "../django-ncharts", "/django-ncharts", folder_options

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  # config.vm.synced_folder "../data", "/vagrant_data"

end
