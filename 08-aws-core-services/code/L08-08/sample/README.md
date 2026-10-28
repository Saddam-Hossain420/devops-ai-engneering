# S3 audit-এর নমুনা (হাতে তৈরি)

প্রতিটি folder একটি bucket; file-গুলো `aws s3api get-*`-এর output-এর রূপে। কোনো file না থাকা = সেই setting কখনো
configure করা হয়নি (AWS তখন `NoSuch…` error দেয়)। Bucket-এর নাম ও account কাল্পনিক।

- `lab08-uploads/` — প্রায় সঠিক: block public access, TLS-only policy, versioning, ownership enforced; lifecycle-এ
  পুরোনো version মোছার নিয়ম নেই।
- `lab08-public-site/` — ইচ্ছাকৃত ভুল: public read policy, block public access বন্ধ, versioning নেই, ACL চালু।
