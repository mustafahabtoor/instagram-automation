from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import os

from database import engine, Base, get_db
from models import ConfigModel, Campaign, ProcessedComment
from instagram import reply_to_comment, send_dm

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Instagram Automation Tool")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    config = db.query(ConfigModel).first()
    campaigns = db.query(Campaign).all()
    return f"""
    <html>
    <head>
        <title>Instagram Automation Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 20px; }}
            .container {{ max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1, h2 {{ color: #333; }}
            form {{ margin-bottom: 20px; padding: 15px; background: #fafafa; border: 1px solid #ddd; border-radius: 5px; }}
            input, textarea {{ width: 100%; padding: 8px; margin: 8px 0; box-sizing: border-box; }}
            button {{ background: #007bff; color: white; border: none; padding: 10px 15px; cursor: pointer; border-radius: 4px; }}
            button:hover {{ background: #0056b3; }}
            .campaign-list {{ border-top: 1px solid #eee; margin-top: 20px; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Instagram Automation Dashboard</h1>
            
            <h2>1. Account Settings</h2>
            <form action="/save-config" method="post">
                <label>Access Token:</label>
                <input type="text" name="access_token" value="{config.access_token if config else ''}" required>
                <label>Page ID:</label>
                <input type="text" name="page_id" value="{config.page_id if config else ''}" required>
                <label>Instagram Business Account ID:</label>
                <input type="text" name="instagram_business_account_id" value="{config.instagram_business_account_id if config else ''}" required>
                <button type="submit">Save Settings</button>
            </form>

            <h2>2. Add New Campaign</h2>
            <form action="/add-campaign" method="post">
                <label>Post ID:</label>
                <input type="text" name="post_id" required>
                <label>Keywords (comma-separated, e.g., price,info,buy):</label>
                <input type="text" name="keywords" required>
                <label>Public Comment Reply:</label>
                <textarea name="comment_reply" rows="2" required></textarea>
                <label>Private Direct Message (DM):</label>
                <textarea name="dm_message" rows="2" required></textarea>
                <button type="submit">Add Campaign</button>
            </form>

            <div class="campaign-list">
                <h2>Active Campaigns</h2>
                {''.join([f"<p><b>Post ID:</b> {c.post_id} | <b>Keywords:</b> {c.keywords}</p>" for c in campaigns]) if campaigns else '<p>No campaigns added yet.</p>'}
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/save-config")
def save_config(access_token: str = Form(...), page_id: str = Form(...), instagram_business_account_id: str = Form(...), db: Session = Depends(get_db)):
    config = db.query(ConfigModel).first()
    if not config:
        config = ConfigModel(access_token=access_token, page_id=page_id, instagram_business_account_id=instagram_business_account_id)
        db.add(config)
    else:
        config.access_token = access_token
        config.page_id = page_id
        config.instagram_business_account_id = instagram_business_account_id
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/add-campaign")
def add_campaign(post_id: str = Form(...), keywords: str = Form(...), comment_reply: str = Form(...), dm_message: str = Form(...), db: Session = Depends(get_db)):
    existing = db.query(Campaign).filter(Campaign.post_id == post_id).first()
    if not existing:
        campaign = Campaign(post_id=post_id, keywords=keywords, comment_reply=comment_reply, dm_message=dm_message, is_active=True)
        db.add(campaign)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/webhook/instagram")
def verify_webhook(request: Request):
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")
    
    verify_token = os.getenv("WEBHOOK_VERIFY_TOKEN", "my_secure_verify_token")
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/webhook/instagram")
async def instagram_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "comments":
                    value = change.get("value", {})
                    comment_id = value.get("id")
                    text = value.get("text", "").lower()
                    media_id = value.get("media", {}).get("id")
                    from_user = value.get("from", {})
                    user_id = from_user.get("id")
                    
                    processed = db.query(ProcessedComment).filter(ProcessedComment.comment_id == comment_id).first()
                    if processed:
                        continue
                    
                    campaign = db.query(Campaign).filter(Campaign.post_id == media_id, Campaign.is_active == True).first()
                    if not campaign:
                        continue
                    
                    keywords_list = [kw.strip().lower() for kw in campaign.keywords.split(",")]
                    matched = any(kw in text for kw in keywords_list)
                    
                    if matched:
                        config = db.query(ConfigModel).first()
                        if config:
                            reply_to_comment(comment_id, campaign.comment_reply, config.access_token)
                            if user_id:
                                send_dm(config.instagram_business_account_id, user_id, campaign.dm_message, config.access_token)
                            
                            new_processed = ProcessedComment(comment_id=comment_id)
                            db.add(new_processed)
                            db.commit()
    except Exception as e:
        print(f"Error processing webhook: {e}")
        
    return {"status": "received"}
