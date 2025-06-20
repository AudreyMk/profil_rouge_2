import os
import json
import sys
import pandas as pd
from datetime import datetime

try:
    from atproto import Client
except ImportError:
    print("Veuillez installer le SDK AT Protocol Python : pip install atproto")
    sys.exit(1)

# Identifiants Bluesky
BLUESKY_IDENTIFIER = 'bbskyprojet.bsky.social'
BLUESKY_APP_PASSWORD = 'n3b7-57x2-m552-lbjv'
OUTPUT_CSV_SEARCH = 'bluesky_search_results.csv'

def search_bluesky_posts(query="Bluesky", limit=100, lang=None):
    client = Client(base_url="https://bsky.social")
    try:
        print(f"Tentative de connexion à Bluesky pour {BLUESKY_IDENTIFIER}...")
        client.login(BLUESKY_IDENTIFIER, BLUESKY_APP_PASSWORD)
        print("Connexion réussie !\n")

        all_posts = []
        cursor = None

        print(f"Recherche de posts contenant '{query}' avec une limite de {limit}...")
        if lang:
            print(f"Filtrage par langue : {lang}")

        while len(all_posts) < limit:
            params = {
                "q": query,
                "limit": min(100, limit - len(all_posts)),
                "cursor": cursor
            }
            if lang:
                params["lang"] = lang

            search_response = client.app.bsky.feed.search_posts(params)
            batch = getattr(search_response, "posts", [])

            print(f"Posts reçus dans ce batch de l'API : {len(batch)}")

            if not batch:
                print("Plus de posts disponibles pour cette recherche.\n")
                break

            for post_view in batch:
                try:
                    record = post_view.record
                    author = post_view.author
                    viewer = getattr(author, 'viewer', None)

                    info = {
                        'post_uri': post_view.uri,
                        'post_url': f"https://bsky.app/profile/{author.handle}/post/{post_view.uri.split('/')[-1]}",
                        'post_cid': post_view.cid,
                        'text': getattr(record, 'text', '').replace('\n', ' ').strip(),
                        'createdAt_post': getattr(record, 'created_at', ''),
                        'indexedAt_post': getattr(post_view, 'indexed_at', ''),
                        'embed': json.dumps(getattr(record, 'embed', {}) or {}, default=str),
                        'likeCount': getattr(post_view, 'like_count', 0),
                        'repostCount': getattr(post_view, 'repost_count', 0),
                        'replyCount': getattr(post_view, 'reply_count', 0),
                        'did': author.did,
                        'handle': author.handle,
                        'displayName': getattr(author, 'display_name', ''),
                        'followersCount': getattr(author, 'followers_count', 0),
                        'followsCount': getattr(author, 'follows_count', 0),
                        'postsCount': getattr(author, 'posts_count', 0),
                        'createdAt_profile': getattr(author, 'created_at', ''),
                        'indexedAt_profile': getattr(author, 'indexed_at', ''),
                        'viewer_muted': getattr(viewer, 'muted', None) if viewer else None,
                        'viewer_following': getattr(viewer, 'following', None) if viewer else None,
                        'viewer_blockedBy': getattr(viewer, 'blocked_by', None) if viewer else None,
                        'labels': json.dumps(getattr(author, 'labels', []) or []),
                        'collectedAt': datetime.utcnow().isoformat() + 'Z'
                    }

                    all_posts.append(info)

                except Exception as post_e:
                    print(f"Erreur lors du traitement du post {getattr(post_view, 'uri', 'inconnu')} : {post_e}")
                    continue

            cursor = getattr(search_response, "cursor", None)
            print(f"Cursor pour la prochaine requête : {cursor}\n")

            if not cursor:
                break

        return all_posts

    except Exception as e:
        print(f"Erreur globale lors de la récupération des posts : {e}")
        return []

def main_search():
    posts_info = search_bluesky_posts(query="Bluesky", limit=500, lang="en")
    if not posts_info:
        print("Aucun post récupéré.")
        return

    df = pd.DataFrame(posts_info)
    df.to_csv(OUTPUT_CSV_SEARCH, index=False, encoding='utf-8', sep=";")
    print(f"\nEnregistré {len(df)} posts dans {OUTPUT_CSV_SEARCH}")

if __name__ == '__main__':
    main_search()





import os
import sys
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
from atproto import Client

# Identifiants Bluesky
BLUESKY_IDENTIFIER = 'bbskyprojet.bsky.social'
BLUESKY_APP_PASSWORD = 'n3b7-57x2-m552-lbjv'
OUTPUT_CSV = 'bluesky_user_posts.csv'

def extract_handle_from_url(profile_url):
    path_parts = urlparse(profile_url).path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == 'profile':
        return path_parts[1]
    return None

def fetch_profile_and_posts(handle, limit=50):
    client = Client(base_url="https://bsky.social")
    client.login(BLUESKY_IDENTIFIER, BLUESKY_APP_PASSWORD)

    # Récupération du profil
    profile = client.app.bsky.actor.get_profile({'actor': handle})

    user_data = {
        'username': profile.handle,
        'user_id': profile.did,
        'bio': getattr(profile, 'description', '').replace('\n', ' ').strip(),
        'followers_count': getattr(profile, 'followers_count', 0),
        'follows_count': getattr(profile, 'follows_count', 0),
        'posts_count': getattr(profile, 'posts_count', 0),
        'profile_created_at': getattr(profile, 'created_at', ''),
    }

    posts = []
    cursor = None

    while len(posts) < limit:
        resp = client.app.bsky.feed.get_author_feed({
            'actor': handle,
            'limit': min(100, limit - len(posts)),
            'cursor': cursor
        })

        for item in resp.feed:
            post = item.post
            record = post.record

            post_data = {
                **user_data,
                'post_uri': post.uri,
                'post_text': getattr(record, 'text', '').replace('\n', ' ').strip(),
                'post_created_at': getattr(record, 'created_at', ''),
                'post_indexed_at': getattr(post, 'indexed_at', ''),
                'like_count': getattr(post, 'like_count', 0),
                'repost_count': getattr(post, 'repost_count', 0),
                'reply_count': getattr(post, 'reply_count', 0),
                'collected_at': datetime.utcnow().isoformat() + 'Z',
            }

            posts.append(post_data)

        cursor = getattr(resp, 'cursor', None)
        if not cursor:
            break

    return posts

def main():
    profile_url_input = input("Entrez l'URL du profil Bluesky (ex: https://bsky.social/profile/bsky.app) : ").strip()
    if not profile_url_input:
        print("❌ Aucune URL entrée. Sortie du programme.")
        return

    handle = extract_handle_from_url(profile_url_input)
    if not handle:
        print("❌ Format de l’URL incorrect. Utilisez une URL de type https://bsky.social/profile/handle")
        return

    posts_info = fetch_profile_and_posts(handle, limit=50)
    if not posts_info:
        print("❌ Aucun post récupéré.")
        return

    df = pd.DataFrame(posts_info)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig', sep=';')
    print(f"✅ Fichier CSV généré avec {len(df)} posts : {OUTPUT_CSV}")

if __name__ == '__main__':
    main()





import sys
import json
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
from atproto import Client

# Identifiants de connexion
BLUESKY_IDENTIFIER = 'bbskyprojet.bsky.social'
BLUESKY_APP_PASSWORD = 'n3b7-57x2-m552-lbjv'
OUTPUT_CSV = 'bluesky_single_post.csv'

def extract_handle_and_post_id(post_url):
    """
    Extrait le handle et l'ID du post depuis une URL de type :
    https://bsky.app/profile/joyousjoyness.com/post/3lgldzhnmes2f
    """
    parsed = urlparse(post_url)
    parts = parsed.path.strip('/').split('/')
    try:
        profile_index = parts.index('profile')
        post_index = parts.index('post')
        handle = parts[profile_index + 1]
        post_id = parts[post_index + 1]
        return handle, post_id
    except (ValueError, IndexError):
        return None, None

def fetch_post_from_url(url):
    client = Client(base_url="https://bsky.social")
    client.login(BLUESKY_IDENTIFIER, BLUESKY_APP_PASSWORD)

    handle, post_id = extract_handle_and_post_id(url)
    if not handle or not post_id:
        print("❌ URL de post Bluesky invalide.")
        sys.exit(1)

    # Résolution du DID depuis le handle
    #resolved = client.app.bsky.actor.resolve_handle({'handle': handle})
    resolved = client.com.atproto.identity.resolve_handle({'handle': handle})
    did = resolved.did

    # Construction de l'URI du post
    uri = f"at://{did}/app.bsky.feed.post/{post_id}"

    # Récupération du post via son URI
    post_thread = client.app.bsky.feed.get_post_thread({'uri': uri})
    post = post_thread.thread.post
    record = post.record

    post_data = {
        'username': handle,
        'user_id': did,
        'post_uri': post.uri,
        'post_cid': post.cid,
        'post_text': getattr(record, 'text', '').replace('\n', ' ').strip(),
        'post_created_at': getattr(record, 'created_at', ''),
        'post_indexed_at': getattr(post, 'indexed_at', ''),
        'like_count': getattr(post, 'like_count', 0),
        'repost_count': getattr(post, 'repost_count', 0),
        'reply_count': getattr(post, 'reply_count', 0),
        'collected_at': datetime.utcnow().isoformat() + 'Z',
    }

    return post_data

def main():
    input_url = input("🔗 Colle l'URL complète du post Bluesky : ").strip()
    post_info = fetch_post_from_url(input_url)

    df = pd.DataFrame([post_info])
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig', sep=';')
    print(f"\n✅ Post exporté avec succès dans le fichier : {OUTPUT_CSV}")

if __name__ == '__main__':
    main()

