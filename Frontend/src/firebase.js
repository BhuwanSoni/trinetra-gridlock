import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

const firebaseConfig = {
  apiKey: "AIzaSyAdgQvyF44xTLdmAxV2fN9UoO2bDAkgPjg",
  authDomain: "hmates-d052b.firebaseapp.com",
  projectId: "hmates-d052b",
  storageBucket: "hmates-d052b.firebasestorage.app",
  messagingSenderId: "547468498580",
  appId: "1:547468498580:web:88a34a1e4fb084f1c50681",
  measurementId: "G-2YR3GVRJTQ"
};

const app = initializeApp(firebaseConfig);

const db = getFirestore(app);
const storage = getStorage(app);

export { db, storage };