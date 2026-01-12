
import json
from datetime import datetime, timedelta
def sync_to_firestore_auto(json_file='footystream_matches.json'):
    """
    Automatically sync JSON data to Firestore without confirmation
    """
    try:
        print("\n" + "="*70)
        print("🔄 STEP 4: Syncing to Firestore...")
        print("="*70 + "\n")
        
        print("🤖 Running in automated mode (no confirmation required)")
        
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        if not matches:
            print("❌ No matches found in JSON file")
            return
        
        # Initialize Firestore sync
        from firebase_admin import credentials, firestore
        import firebase_admin
        
        if not firebase_admin._apps:
            cred = credentials.Certificate('serviceAccountKey.json')
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        collection = db.collection('matches')
        
        print(f"✅ Connected to Firestore")
        print(f"📁 Collection: matches")
        print(f"📊 Loaded {len(matches)} matches from {json_file}\n")
        
        # STEP 1: Delete all existing documents
        print(f"🗑️  Deleting all existing documents from 'matches'...")
        docs = list(collection.stream())
        deleted_count = 0
        
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
            print(f"  🗑️  Deleted: {doc.id}")
        
        print(f"\n✓ Deleted {deleted_count} document(s)\n")
        
        # STEP 2: Add all new documents
        print(f"➕ Adding {len(matches)} new documents to Firestore...")
        
        stats = {'added': 0, 'errors': 0}
        
        for match in matches:
            doc_id = match.get('doc_id')
            
            if not doc_id:
                print(f"⚠️  Skipping match without doc_id: {match.get('title', 'Unknown')}")
                stats['errors'] += 1
                continue
            
            try:
                sync_data = match.copy()
                sync_data['syncedAt'] = datetime.now().isoformat()
                
                collection.document(doc_id).set(sync_data)
                stats['added'] += 1
                print(f"  ➕ Added: {match.get('title', 'Unknown')} (ID: {doc_id})")
                
            except Exception as e:
                print(f"  ❌ ERROR adding {doc_id}: {e}")
                stats['errors'] += 1
        
        # Print summary
        print("\n" + "="*70)
        print("📊 FIRESTORE SYNC SUMMARY")
        print("="*70)
        print(f"🗑️  Deleted:   {deleted_count}")
        print(f"➕ Added:     {stats['added']}")
        print(f"❌ Errors:    {stats['errors']}")
        print(f"📝 Total:     {len(matches)}")
        print("="*70)
        
        print("\n✅ Firestore sync completed successfully!")
        print(f"💾 Firestore collection now contains {stats['added']} document(s)")
        
    except Exception as e:
        print(f"\n❌ Error syncing to Firestore: {e}")
        import traceback
        traceback.print_exc()
