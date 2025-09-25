import boto3
import botocore.config
import json

def blog_generate(topic: str) -> str:
    prompt = f"Write a 300 words blog on the topic: {topic}"
    model_id = "us.deepseek.r1-v1:0"

    # Correct DeepSeek R1 format
    formatted_prompt = f"<|begin_of_sentence|><|User|>{prompt}<|Assistant|><think>\n"

    body = json.dumps({
        "prompt": formatted_prompt,
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.9,
        "stop": []
    })

    client = boto3.client(
        service_name="",
        region_name="us-east-1",
        config=botocore.config.Config(read_timeout=300, retries={'max_attempts': 3})
    )

    try:
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body
        )
        result = json.loads(response["body"].read())
        print("Raw response:", result)

        # DeepSeek R1 returns text under choices[0]["text"]
        if "choices" in result and result["choices"]:
            return result["choices"][0]["text"]
        elif "text" in result:
            return result["text"]
        else:
            return str(result)

    except Exception as e:
        print(f"Error invoking DeepSeek R1: {e}")
        raise


def save_blog(s3_key, s3_bucket, generate_blog):
    s3 = boto3.client("s3")
    try:
        s3.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=generate_blog.encode("utf-8"),
            ContentType="text/plain"
        )
        print(f"Saved to S3: s3://{s3_bucket}/{s3_key}")
    except Exception as e:
        print(f"Couldn't save to S3 bucket. Error: {e}")
        raise


def lambda_handler(event, context):
    try:
        # Parse incoming request
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        topic = body.get("blog_topic")
        if not topic:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": "Missing 'blog_topic' in request"})
            }

        # Generate blog content
        generate_blog = blog_generate(topic=topic)

        if generate_blog:
            s3_key = f"blog-output-{topic.replace(' ', '_').replace('/', '_')}.txt"
            s3_bucket = ""
            save_blog(s3_key, s3_bucket, generate_blog)

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "message": "Blog generated successfully",
                    "s3_location": f"s3://{s3_bucket}/{s3_key}",
                    "content_preview": generate_blog[:100] + "..." if len(generate_blog) > 100 else generate_blog
                })
            }
        else:
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": "No blog was generated"})
            }

    except Exception as e:
        print(f"Lambda handler error: {e}")
        raise
