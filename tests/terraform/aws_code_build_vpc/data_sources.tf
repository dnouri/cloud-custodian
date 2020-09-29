data "aws_vpc" "example" {
  filter {
    name   = "tag:Name"
    values = ["example"]
  }
}


data "aws_subnet" "example" {
  filter {
    name   = "tag:Name"
    values = ["example"]
  }
}

data "aws_security_group" "example1" {
  filter {
    name   = "tag:Name"
    values = ["example"]
  }
}
