terraform {
  required_version = ">= 1.5"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
  }
}

variable "compartment_id" {
  type        = string
  description = "OCI compartment OCID"
}

variable "region" {
  default     = "us-ashburn-1"
  type        = string
  description = "OCI region"
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key for platform VM"
}

# Oracle Cloud Free Tier: VM.Standard.A1.Flex (4 OCPU, 24 GB RAM)
resource "oci_core_vcn" "iicpc_vcn" {
  compartment_id = var.compartment_id
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "iicpc-vcn"
  dns_label      = "iicpc"
}

resource "oci_core_subnet" "public_subnet" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.iicpc_vcn.id
  cidr_block     = "10.0.1.0/24"
  display_name   = "iicpc-public"
  dns_label      = "public"
  security_list_ids = [oci_core_security_list.platform_sl.id]
  route_table_id    = oci_core_route_table.public_rt.id
}

resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.iicpc_vcn.id
  display_name   = "iicpc-igw"
  enabled        = true
}

resource "oci_core_route_table" "public_rt" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.iicpc_vcn.id
  display_name   = "public-rt"
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.igw.id
  }
}

resource "oci_core_security_list" "platform_sl" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.iicpc_vcn.id
  display_name   = "platform-sl"
  ingress_security_rules {
    protocol = "6"
    tcp_options { min = 22; max = 22 }
    source   = "0.0.0.0/0"
  }
  ingress_security_rules {
    protocol = "6"
    tcp_options { min = 3000; max = 3000 }
    source   = "0.0.0.0/0"
  }
  ingress_security_rules {
    protocol = "6"
    tcp_options { min = 8000; max = 8000 }
    source   = "0.0.0.0/0"
  }
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}

resource "oci_core_instance" "platform" {
  compartment_id      = var.compartment_id
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "iicpc-platform"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu_arm.images[0].id
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public_subnet.id
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(<<-EOF
      #!/bin/bash
      curl -fsSL https://get.docker.com | sh
      git clone https://github.com/YOUR_USER/iicpc-platform.git /opt/iicpc
      cd /opt/iicpc && make demo
    EOF
    )
  }
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}

data "oci_core_images" "ubuntu_arm" {
  compartment_id           = var.compartment_id
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

output "platform_public_ip" {
  value = oci_core_instance.platform.public_ip
}

output "quickstart_ssh" {
  value = "ssh ubuntu@${oci_core_instance.platform.public_ip}"
}
