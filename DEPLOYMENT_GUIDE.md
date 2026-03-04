# Deployment Guide for Rwanda Healthcare Dashboard

## Option 1: Deploy to Streamlit Community Cloud (Recommended - Free)

### Prerequisites
1. GitHub account (free at https://github.com)
2. Streamlit Cloud account (free at https://streamlit.io/cloud)

### Step-by-Step Instructions

#### 1. Create GitHub Repository

1. Go to https://github.com and sign in
2. Click the "+" icon in top-right corner
3. Select "New repository"
4. Name it: `rwanda-healthcare-dashboard`
5. Set to **Private** (for data security) or Public
6. Click "Create repository"

#### 2. Push Code to GitHub

Run these commands in Terminal:

```bash
# Navigate to project directory
cd "/Users/nhiclap001/Desktop/MoH Leadership/Health Facility Mapping/Health Centers"

# Add all files
git add .

# Commit files
git commit -m "Initial commit: Rwanda Healthcare Dashboard"

# Add your GitHub repository as remote (replace with your URL)
git remote add origin https://github.com/YOUR_USERNAME/rwanda-healthcare-dashboard.git

# Push to GitHub
git branch -M main
git push -u origin main
```

#### 3. Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click "New app"
4. Fill in the form:
   - Repository: `YOUR_USERNAME/rwanda-healthcare-dashboard`
   - Branch: `main`
   - Main file path: `rwanda_dashboard_optimized_final.py`
5. Click "Deploy"

#### 4. Configure Secrets (Important!)

Since your app uses a Mapbox token, add it to Streamlit secrets:

1. In Streamlit Cloud dashboard, click on your app
2. Click "Settings" → "Secrets"
3. Add:
```toml
MAPBOX_TOKEN = "your-mapbox-token-here"
```

#### 5. Share Your App

Once deployed, you'll get a URL like:
`https://your-app-name.streamlit.app`

Share this link with others!

---

## Option 2: Deploy to Heroku (Requires Credit Card)

### Prerequisites
- Heroku account (https://heroku.com)
- Heroku CLI installed

### Files Needed

Create `setup.sh`:
```bash
mkdir -p ~/.streamlit/

echo "\
[server]\n\
headless = true\n\
port = \$PORT\n\
enableCORS = false\n\
\n\
" > ~/.streamlit/config.toml
```

Create `Procfile`:
```
web: sh setup.sh && streamlit run rwanda_dashboard_optimized_final.py
```

### Deploy Commands
```bash
heroku create your-app-name
git add .
git commit -m "Prepare for Heroku deployment"
git push heroku main
```

---

## Option 3: Deploy to AWS EC2 (More Complex)

### Prerequisites
- AWS account
- EC2 instance (t2.micro for free tier)

### Steps
1. Launch EC2 instance with Ubuntu
2. SSH into instance
3. Install Python and dependencies
4. Clone repository
5. Run with `streamlit run --server.port 8501 --server.address 0.0.0.0`
6. Configure security group to allow port 8501

---

## Important Considerations

### Data Files
⚠️ **Large Data Files**: If your data files are too large for GitHub (>100MB), you have options:

1. **Use Git LFS** (Large File Storage):
```bash
git lfs track "*.csv"
git lfs track "*.xlsx"
git lfs track "*.gpkg"
git add .gitattributes
```

2. **Use Cloud Storage** (AWS S3, Google Cloud Storage):
   - Upload files to cloud storage
   - Modify app to download from cloud

3. **Use Streamlit's File Uploader**:
   - Modify app to allow users to upload data files
   - More secure for sensitive data

### Security
- Never commit sensitive data to public repositories
- Use environment variables for API keys
- Consider data privacy regulations

### Performance
- The free Streamlit Cloud tier has resource limits:
  - 1 GB of RAM
  - 1 GB of storage
- For better performance, consider paid tiers

---

## Troubleshooting

### Common Issues

1. **"Module not found" error**
   - Ensure all dependencies are in requirements.txt

2. **App crashes or runs slowly**
   - Optimize data loading with caching
   - Reduce data size if possible

3. **Map not showing**
   - Verify Mapbox token is correctly set in secrets

4. **File not found errors**
   - Check file paths are relative, not absolute
   - Ensure all data files are committed

---

## Quick Start Commands

```bash
# 1. Prepare for deployment
cd "/Users/nhiclap001/Desktop/MoH Leadership/Health Facility Mapping/Health Centers"

# 2. Check what will be committed
git status

# 3. Add all files
git add .

# 4. Commit
git commit -m "Deploy Rwanda Healthcare Dashboard"

# 5. Push to GitHub (after creating repo)
git push origin main
```

---

## Support

For Streamlit Cloud issues: https://docs.streamlit.io/streamlit-community-cloud
For GitHub issues: https://docs.github.com

---

## Next Steps After Deployment

1. Test the deployed app thoroughly
2. Share the link with stakeholders
3. Monitor usage and performance
4. Set up automatic updates with GitHub Actions (optional)
5. Consider adding authentication if needed