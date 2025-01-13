aws cloudformation create-stack \
    --stack-name pca-sftp-server \
    --template-body file://./aws-transfer-family-sftp.template.yaml \
    --parameters file://./aws-transfer-family-sftp-params.json \
    --capabilities CAPABILITY_IAM