import json
import time
import hashlib
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore


class RealtimeFirestoreSync:
    def __init__(self, service_account_path='serviceAccountKey.json', collection_name='matches'):
        """
        Initialize Firestore connection with real-time sync capabilities
        
        Args:
            service_account_path: Path to Firebase service account JSON
            collection_name: Firestore collection name
        """
        self.collection_name = collection_name
        self.json_file = 'footystream_matches.json'
        self.last_hash = None
        
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        self.collection = self.db.collection(collection_name)
        
        print(f"✅ Connected to Firestore")
        print(f"📁 Collection: {collection_name}")
        print(f"📄 Watching file: {self.json_file}")
    
    def load_json_data(self):
        """Load matches from JSON file"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ File {self.json_file} not found!")
            return []
        except json.JSONDecodeError:
            print(f"❌ Error reading {self.json_file}!")
            return []
    
    def get_file_hash(self):
        """Calculate hash of JSON file to detect changes"""
        try:
            with open(self.json_file, 'rb') as f:
                file_content = f.read()
                return hashlib.md5(file_content).hexdigest()
        except FileNotFoundError:
            return None
    
    def has_file_changed(self):
        """Check if JSON file has changed since last check"""
        current_hash = self.get_file_hash()
        
        if current_hash is None:
            return False
        
        if self.last_hash is None:
            self.last_hash = current_hash
            return True  # First run
        
        if current_hash != self.last_hash:
            self.last_hash = current_hash
            return True
        
        return False
    
    def get_all_firestore_docs(self):
        """Get all document IDs from Firestore"""
        docs = self.collection.stream()
        return {doc.id: doc.to_dict() for doc in docs}
    
    def has_changes(self, local_data, firestore_data):
        """Compare local data with Firestore data to detect changes"""
        if not firestore_data:
            return True  # New document
        
        for key, value in local_data.items():
            if key in ['syncedAt', 'lastCheckedAt']:
                continue
            if value != firestore_data.get(key):
                return True
        
        return False
    
    def sync_to_firestore(self):
        """Sync JSON data to Firestore"""
        # Load local JSON data
        matches = self.load_json_data()
        
        if not matches:
            print("⚠️  No matches found in JSON file")
            return {'added': 0, 'updated': 0, 'unchanged': 0, 'errors': 0}
        
        # Get all existing Firestore documents
        firestore_docs = self.get_all_firestore_docs()
        
        # Track statistics
        stats = {
            'added': 0,
            'updated': 0,
            'unchanged': 0,
            'errors': 0
        }
        
        # Process each match
        for match in matches:
            doc_id = match.get('doc_id')
            
            if not doc_id:
                stats['errors'] += 1
                continue
            
            try:
                # Get existing Firestore data
                existing_data = firestore_docs.get(doc_id)
                
                # Prepare data for Firestore
                sync_data = match.copy()
                sync_data['syncedAt'] = datetime.now().isoformat()
                
                # Check if document needs updating
                if self.has_changes(match, existing_data):
                    if existing_data:
                        # Update existing document
                        stats['updated'] += 1
                        print(f"  🔄 Updated: {match.get('title', 'Unknown')}")
                        self.collection.document(doc_id).set(sync_data, merge=True)
                    else:
                        # Add new document
                        stats['added'] += 1
                        print(f"  ➕ Added: {match.get('title', 'Unknown')}")
                        self.collection.document(doc_id).set(sync_data)
                else:
                    stats['unchanged'] += 1
                
            except Exception as e:
                print(f"  ❌ ERROR syncing {doc_id}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def watch_and_sync(self, check_interval=60):
        """
        Continuously watch JSON file and sync changes to Firestore
        
        Args:
            check_interval: Seconds between checks (default: 60)
        """
        print("\n" + "="*70)
        print("🔄 REAL-TIME FIRESTORE SYNC STARTED")
        print("="*70)
        print(f"⏱️  Check interval: {check_interval} seconds")
        print(f"👀 Watching for changes in: {self.json_file}")
        print(f"🔥 Syncing to Firestore collection: {self.collection_name}")
        print("="*70 + "\n")
        
        iteration = 0
        
        while True:
            try:
                iteration += 1
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"🔍 Check #{iteration} - {current_time}")
                
                # Check if file has changed
                if self.has_file_changed():
                    print(f"📝 Changes detected in {self.json_file}!")
                    print(f"🔄 Syncing to Firestore...")
                    
                    stats = self.sync_to_firestore()
                    
                    # Print summary
                    if stats['added'] > 0 or stats['updated'] > 0:
                        print(f"\n✅ Sync completed:")
                        if stats['added'] > 0:
                            print(f"   ➕ Added: {stats['added']}")
                        if stats['updated'] > 0:
                            print(f"   🔄 Updated: {stats['updated']}")
                        if stats['errors'] > 0:
                            print(f"   ❌ Errors: {stats['errors']}")
                    else:
                        print(f"✓ No changes needed (all up to date)")
                else:
                    print(f"✓ No file changes detected")
                
                # Wait for next check
                next_check = datetime.now()
                next_check = next_check.replace(second=0, microsecond=0)
                # Add check_interval seconds
                import datetime as dt
                next_check = next_check + dt.timedelta(seconds=check_interval)
                print(f"⏳ Next check at: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"💤 Sleeping for {check_interval} seconds...\n")
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n\n👋 Real-time sync stopped by user")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
                print(f"\n⏳ Continuing in {check_interval} seconds...\n")
                time.sleep(check_interval)


def main():
    """Main entry point"""
    import sys
    
    # Parse command line arguments
    check_interval = 60  # Default: 60 seconds
    
    if len(sys.argv) > 1:
        try:
            check_interval = int(sys.argv[1])
            if check_interval < 1:
                print("⚠️  Check interval must be at least 1 second. Using 60 seconds.")
                check_interval = 60
        except ValueError:
            print("⚠️  Invalid interval. Using default: 60 seconds")
    
    # Create sync instance
    sync = RealtimeFirestoreSync(
        service_account_path='serviceAccountKey.json',
        collection_name='matches'
    )
    
    try:
        # Start watching and syncing
        sync.watch_and_sync(check_interval=check_interval)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    """
    Usage:
        # Watch and sync every 60 seconds (default)
        python realtime_sync.py
        
        # Watch and sync every 30 seconds
        python realtime_sync.py 30
        
        # Watch and sync every 2 minutes (120 seconds)
        python realtime_sync.py 120
    """
    main()