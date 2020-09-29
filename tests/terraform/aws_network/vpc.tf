resource "aws_vpc" "example" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "example" {
  vpc_id     = aws_vpc.example.id
  cidr_block = "10.0.1.0/24"
}

output "aws_vpc_example_id" {
  value = aws_vpc.example.id
}

output "aws_subnet_example_id" {
  value = aws_subnet.example.id
}

output "aws_subnet_example_arn" {
  value = aws_subnet.example.arn
}
