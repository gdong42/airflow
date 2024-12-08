from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from typing import Optional

app = FastAPI()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
AIRFLOW_BASE_URL = "http://localhost:28080"
# You might want to store this securely in environment variables
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "Basic YWRtaW46YWRtaW4=")

async def forward_request(request: Request, path: str) -> httpx.Response:
    # Get the target URL
    target_url = f"{AIRFLOW_BASE_URL}{path}"
    
    # Get request body if present
    body = await request.body()
    
    # Get query parameters
    params = dict(request.query_params)
    
    # Get headers and add authentication
    headers = dict(request.headers)
    headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    
    # Remove headers that might cause issues
    headers.pop("host", None)
    # headers.pop("content-length", None)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                params=params,
                headers=headers,
                content=body,
                follow_redirects=True
            )
            return response
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy(request: Request, path: str):
    response = await forward_request(request, f"/{path}")
    
    # Return the response with the same status code and headers
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 