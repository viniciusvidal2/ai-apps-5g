const { drizzle } = require('drizzle-orm/postgres-js');
const postgres = require('postgres');
const { eq } = require('drizzle-orm');

// Define the user table schema inline
const user = {
  id: 'id',
  email: 'email',
  password: 'password'
};

async function createFixedGuest() {
  const connectionString = process.env.POSTGRES_URL;
  const client = postgres(connectionString);
  const db = drizzle(client);

  try {
    // Check if guest already exists
    const existingGuest = await db.execute(
      `SELECT * FROM "User" WHERE email = 'guest-fixed@temp.com'`
    );
    
    if (existingGuest.length === 0) {
      // Create fixed guest user
      await db.execute(`
        INSERT INTO "User" (id, email, password) 
        VALUES ('00000000-0000-0000-0000-000000000001', 'guest-fixed@temp.com', 'dummy_password')
      `);
      console.log('Fixed guest user created successfully');
    } else {
      console.log('Fixed guest user already exists');
    }
  } catch (error) {
    console.error('Error creating fixed guest user:', error);
  } finally {
    await client.end();
  }
}

createFixedGuest();
