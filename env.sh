export AWS_PROFILE=pcaprod
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
export AWS_PAGER=cat
export AWS_ACCOUNT_ID=495599748176

export PCA_VERSION=`cat VERSION`
export PCA_ADMIN_EMAIL=pedro.castro@digitalrisk.com

export PCA_DEPLOY_BUCKET=pca-deploy-artifacts-${AWS_ACCOUNT_ID}

export PCA_TELEPHONY_TYPE=none
export PCA_PRELOAD_BUCKET_NAME=pca-inbound-call-files-${AWS_ACCOUNT_ID}
export PCA_PRELOAD_OBJECT_KEY_REGEX='.xml$'